from flask import Flask, render_template, request, redirect, url_for, session
import requests
import psycopg2
import psycopg2.extras
import os
import random
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from psycopg2 import pool
from api.extensions.db import *

def refresh_due_player_times():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM players WHERE last_updated IS NULL OR last_updated < NOW() - INTERVAL '1 day'"
            )
            due_players = cur.fetchall()
    finally:
        release_db(conn)

    for player in due_players:
        update_player_times(player)


def update_player_times(player):
    track_results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(fetch_time, player['token_hash'], track_id): track_name for track_id, track_name in TRACKS}
        for future in as_completed(futures):
            track_name = futures[future]
            frames = future.result()
            if frames is not None:
                track_results[track_name] = frames

    if not track_results:
        return

    conn = get_db()
    try:
        with conn.cursor() as cur:
            for track_name, frames in track_results.items():
                cur.execute(
                    '''
                    INSERT INTO player_times (player_id, track_name, frames)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (player_id, track_name) DO UPDATE
                    SET frames = EXCLUDED.frames,
                        updated_at = NOW()
                    ''',
                    (player['id'], track_name, frames)
                )
            cur.execute('UPDATE players SET last_updated = NOW() WHERE id = %s', (player['id'],))
        conn.commit()
    finally:
        release_db(conn)

def frames_to_time(frames):
    total_ms = frames
    minutes = total_ms // 60000
    seconds = (total_ms % 60000) // 1000
    ms = total_ms % 1000
    return f"{minutes}:{seconds:02d}.{ms:03d}"

def fetch_time(token_hash, track_id):
    try:
        url = (
            f"https://vps.kodub.com/v6/leaderboard"
            f"?version=0.6.0&skip=0&amount=1&onlyVerified=false"
            f"&trackId={track_id}&userTokenHash={token_hash.strip()}"
        )
        r = requests.get(url, timeout=5)
        data = r.json()
        entry = data.get('userEntry')
        if entry and entry.get('frames'):
            return entry['frames']
    except Exception:
        pass
    return None

def fetch_track_leaderboard(track_name):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT p.nickname, pt.frames
                FROM players p
                JOIN player_times pt ON p.id = pt.player_id
                WHERE pt.track_name = %s AND pt.frames IS NOT NULL
                ORDER BY pt.frames
            ''', (track_name,))
            rows = cur.fetchall()
    finally:
        release_db(conn)

    results = []
    for row in rows:
        results.append({
            'nickname': row['nickname'],
            'frames': row['frames'],
            'time': frames_to_time(row['frames']),
        })

    for i, r in enumerate(results):
        r['rank'] = i + 1
    return results

def fetch_overall_leaderboard():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT p.id, p.nickname, pt.track_name, pt.frames
                FROM players p
                LEFT JOIN player_times pt ON p.id = pt.player_id
                ORDER BY p.id
            ''')
            rows = cur.fetchall()
    finally:
        release_db(conn)

    player_data = {}
    for row in rows:
        pid = row['id']
        if pid not in player_data:
            player_data[pid] = {'nickname': row['nickname'], 'times': {}}
        if row['track_name'] and row['frames']:
            player_data[pid]['times'][row['track_name']] = row['frames']

    results = []
    for pid, data in player_data.items():
        times = data['times']
        if not times:
            continue
        total = sum(times.values())
        completed = len(times)
        results.append({
            'nickname': data['nickname'],
            'total_frames': total,
            'total_time': frames_to_time(total),
            'completed': completed,
            'total_tracks': len(TRACKS),
            'times': {k: frames_to_time(v) for k, v in times.items()},
        })

    results.sort(key=lambda x: (-(x['completed']), x['total_frames']))
    for i, r in enumerate(results):
        r['rank'] = i + 1
    return results