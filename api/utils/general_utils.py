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

def generate_code():
    return f"{random.randint(0, 999999):06d}"


def send_sign_in_code(email, code):
    resend_key = os.environ.get('RESEND_KEY')
    if not resend_key:
        print(f'[AUTH] Sign-in code for {email}: {code}')
        return

    try:
        response = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {resend_key}'},
            json={
                'from': 'K-Engage <noreply@kclms.app>',
                'to': email,
                'subject': 'Your K-Engage sign-in code',
                'text': f'Your K-Engage sign-in code is: {code}\nIt expires in 10 minutes.',
                'html': f'<p>Your K-Engage sign-in code is: <strong>{code}</strong></p><p>It expires in 10 minutes.</p>',
            }
        )
        if response.status_code not in (200, 201):
            print(f'[AUTH] Could not send email to {email}. Code: {code}')
    except Exception as e:
        print(f'[AUTH] Email error for {email}: {e}. Code: {code}')


def can_edit_notices():
    return session.get('user_email') in AUTHORIZED_EDITORS
