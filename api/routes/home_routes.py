from flask import Flask, Blueprint, render_template, request, redirect, url_for, session
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
from api.utils.general_utils import *
from api.utils.polytrack_utils import *

home_blueprint = Blueprint('home', __name__, url_prefix="/home")

@home_blueprint.route('/')
def home():
    init_db()
    refresh_due_player_times()
    leaderboard = fetch_overall_leaderboard()
    return render_template(
        'home.html',
        user_email=session.get('user_email'),
        leaderboard=leaderboard[:5],
        notices=NOTICES,
        forum_posts=FORUM_POSTS,
        can_edit=can_edit_notices(),
        homework_calendar=HOMEWORK_CALENDAR,
    )

@home_blueprint.route('/add-notice', methods=['POST'])
def add_notice():
    if not can_edit_notices():
        return redirect(url_for('home.home'))
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    if title and message:
        NOTICES.insert(0, {
            'title': title,
            'message': message,
            'author': session.get('user_email'),
            'created_at': datetime.utcnow().strftime('%b %d %Y %H:%M'),
        })
    return redirect(url_for('home.home'))

@home_blueprint.route('/add-forum', methods=['POST'])
def add_forum():
    if not can_edit_notices():
        return redirect(url_for('home.home'))
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    if subject and message:
        FORUM_POSTS.insert(0, {
            'subject': subject,
            'message': message,
            'author': session.get('user_email'),
            'created_at': datetime.utcnow().strftime('%b %d %Y %H:%M'),
        })
    return redirect(url_for('home.home'))