from flask import Flask, render_template, request, redirect, url_for
import requests
import psycopg2
import psycopg2.extras
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from psycopg2 import pool

app = Flask(__name__)

load_dotenv()
DATABASE_URL = os.environ['DATABASE_URL']

# Connection pool for better serverless performance
db_pool = pool.SimpleConnectionPool(1, 5, DATABASE_URL, sslmode='require', cursor_factory=psycopg2.extras.RealDictCursor)

TRACKS = [
    ('5803f9e963625804e3de3246d043dc7dde847aa32e991f7f7326b0453f1fa038', 'S1'),
    ('7eac4fee1111152cfba4d3737410264ca0f22c7f5a2211e79f0099589b8b48c0', 'S2'),
    ('148826aa16ffaa23dbc453b32cff05e025ddbce1773fc7733cc13d218926515a', 'S3'),
    ('93c7363dfea7fb09ca1d23b72cad5df43a30841d41c8ff25fb544c85bb03c7ae', 'S4'),
    ('7603aaeffa1989a649dfaa8e1804bed4481b49df233e377687d0669899566e52', 'S5'),
    ('c117823cf6788e3247b9ee63a0c091c07352bbe352c650a7790dc6718148c2fa', 'S6'),
    ('e4bcaca3a583bb0eb62a700a69d14e89c852f0c5bf740fca76e0519ebdfc9ab1', 'S7'),
    ('7239b17057127936907a805b0caa5d8c6f6c97eca9bdabf1a5312dce479629b7', 'W1'),
    ('99864b635d1891d22e17eb9267527a07a92c49c0f02893729fa2ded90e3ca0f9', 'W2'),
    ('a5341fe706097cff2a3812a3fc0d87399254557328351ae8e5c882700fc1a196', 'W3'),
    ('7d134c939df80c676a258266201beedd3b93572d5603f3ff4339ff8679803715', 'W4'),
    ('2fe4bd46b0075cc25fc770ce50adbb68447cf493c999635bb272d231811dd264', 'W5'),
    ('c20b4ee3cd517ca6cae7e43f047548757287fbd08ba81b97892a3ef520159a34', 'D1'),
    ('88647ea04145fbbbb19b55f1590e038fb0378acb2571110f02cb545cc46b0d57', 'D2'),
    ('2806030c503abb41a1a26fa9a570888be14296172bb273798ef0ad87a108a2ec', 'D3'),
    ('4697ea67b18c3f49b30a3d8884602115536650bc5435c88e3732e64d21a72d33', 'D4'),
    ('e5d084e06db4ab71196fea44efeceb23c8561266a78669c324a38f92581fe2db', 'D5'),
]
TRACK_IDS = {name: tid for tid, name in TRACKS}
TRACK_NAMES = [name for _, name in TRACKS]

def get_db():
    return db_pool.getconn()

def release_db(conn):
    db_pool.putconn(conn)

def init_db():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id SERIAL PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    last_updated TIMESTAMP WITH TIME ZONE
                )
            ''')
            cur.execute('''
                CREATE TABLE IF NOT EXISTS player_times (
                    id SERIAL PRIMARY KEY,
                    player_id INTEGER NOT NULL REFERENCES players(id) ON DELETE CASCADE,
                    track_name TEXT NOT NULL,
                    frames INTEGER,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    UNIQUE(player_id, track_name)
                )
            ''')
        conn.commit()
    finally:
        release_db(conn)

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

@app.route('/polytrack')
def polytrack_index():
    init_db()
    refresh_due_player_times()

    track = request.args.get('track')
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('SELECT * FROM players')
            players = cur.fetchall()
    finally:
        release_db(conn)

    if track and track in TRACK_IDS:
        leaderboard = fetch_track_leaderboard(track)
        mode = 'track'
    else:
        leaderboard = fetch_overall_leaderboard()
        mode = 'overall'
        track = None

    return render_template(
        'polytrack.html',
        tracks=TRACK_NAMES,
        leaderboard=leaderboard,
        mode=mode,
        active_track=track,
        player_count=len(players),
    )

@app.route('/polytrack/register', methods=['POST'])
def register():
    nickname = request.form.get('nickname', '').strip()
    token_hash = request.form.get('token_hash', '').strip()
    if not nickname or not token_hash:
        return redirect(url_for('polytrack_index'))
    try:
        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    'INSERT INTO players (nickname, token_hash) VALUES (%s, %s) ON CONFLICT (token_hash) DO NOTHING',
                    (nickname, token_hash)
                )
                conn.commit()
                cur.execute('SELECT id, nickname, token_hash FROM players WHERE token_hash = %s', (token_hash,))
                player = cur.fetchone()
        finally:
            release_db(conn)
        if player:
            update_player_times(player)
    except Exception:
        pass
    return redirect(url_for('polytrack_index'))

@app.route('/polytrack/delete/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM players WHERE id = %s', (player_id,))
        conn.commit()
    finally:
        release_db(conn)
    return redirect(url_for('polytrack_index'))

if __name__ == '__main__':
    app.run(debug=True)