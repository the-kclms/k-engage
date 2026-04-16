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
from api.config import *

# NOTE: we keep all imports here as alot of programs actually do require the imports
# stemmed from this file, it would be tedious to replace them

db_pool = pool.SimpleConnectionPool(1, 5, DATABASE_URL, sslmode='require', cursor_factory=psycopg2.extras.RealDictCursor)

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