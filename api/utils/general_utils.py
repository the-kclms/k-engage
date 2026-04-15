import random

import requests
from flask import session

from api.config import *

# Hold general purpose utility functions for K-ENGAGE

def generate_code():
    return f"{random.randint(0, 999999):06d}"


def send_sign_in_code(email, code):
    try:
        url = "https://eo9hhcmknwji8jn.m.pipedream.net"
        data = {
            "email": email,
            "code": code
        }
        requests.post(url, json=data)
        return
    except Exception as e:
        print(f'[AUTH] Email error for {email}: {e}. Code: {code}')


def can_edit_notices():
    return session.get('user_email') in AUTHORIZED_EDITORS
