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

auth_blueprint = Blueprint('auth', __name__)

@auth_blueprint.before_request
def require_login():
    public_endpoints = {'auth.sign_in', 'auth.send_code', 'auth.verify_code', 'static'}
    if request.endpoint not in public_endpoints and 'user_email' not in session:
        return redirect(url_for('auth.sign_in'))

@auth_blueprint.route('/', methods=['GET'])
def sign_in():
    if 'user_email' in session:
        return redirect(url_for('home.home'))
    return render_template('sign_in.html', email='', success=None, error=None, show_code_field=False)

@auth_blueprint.route('/send-code', methods=['POST'])
def send_code():
    email = request.form.get('email', '').strip().lower()
    if not email.endswith('@kcl.ac.uk'):
        return render_template('sign_in.html', email=email, error='Email must end with @kcl.ac.uk.', success=None, show_code_field=False)

    code = generate_code()
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    SIGNIN_CODES[email] = {
        'code': code,
        'expires_at': expires_at,
        'used': False,
    }

    send_sign_in_code(email, code)
    return render_template('sign_in.html', email=email, success='Code sent. Check your KCL email.', error=None, show_code_field=True)

@auth_blueprint.route('/verify-code', methods=['POST'])
def verify_code():
    email = request.form.get('email', '').strip().lower()
    code = request.form.get('code', '').strip()
    if not email.endswith('@kcl.ac.uk') or len(code) != 6:
        return render_template('sign_in.html', email=email, error='Invalid email or code.', success=None, show_code_field=True)

    auth_row = SIGNIN_CODES.get(email)
    if not auth_row or auth_row['code'] != code:
        return render_template('sign_in.html', email=email, error='Code not found.', success=None, show_code_field=True)
    if auth_row['used']:
        return render_template('sign_in.html', email=email, error='Code has already been used.', success=None, show_code_field=True)
    if auth_row['expires_at'] < datetime.utcnow():
        return render_template('sign_in.html', email=email, error='Code has expired.', success=None, show_code_field=True)

    auth_row['used'] = True
    session['user_email'] = email
    return redirect(url_for('home.home'))

@auth_blueprint.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('auth.sign_in'))