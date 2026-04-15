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

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'didheblud')

load_dotenv()
DATABASE_URL = os.environ['DATABASE_URL']

# Connection pool for better serverless performance
db_pool = pool.SimpleConnectionPool(1, 5, DATABASE_URL, sslmode='require', cursor_factory=psycopg2.extras.RealDictCursor)

# In-memory sign-in codes; reset on server restart.
SIGNIN_CODES = {}
AUTHORIZED_EDITORS = ['max.fletcher@kcl.ac.uk', 'arka.goswami@kcl.ac.uk', 'victor.oluwafemi@kcl.ac.uk', 'kavan.vyas@kcl.ac.uk']
NOTICES = [
    {'title': 'Welcome to K-Engage', 'message': 'Check the games and homework cards every day.', 'author': 'System', 'created_at': 'Today'},
]
FORUM_POSTS = [
    {'author': 'student@kcl.ac.uk', 'subject': 'Polytrack setup', 'message': 'Does anyone know how to add a player?', 'created_at': 'Today'},
]
HOMEWORK_CALENDAR = [
    {'subject': 'Core', 'due': 'Every Monday', 'class': '12MOO'},
    {'subject': 'Stats', 'due': 'Every Tuesday', 'class': '12MAO'},
    {'subject': 'Mech', 'due': 'Every Wednesday', 'class': '12MEO'},
    {'subject': 'Physics Johnson', 'due': 'Every Thursday', 'class': '12PHYJ'},
    {'subject': 'Physics Rubin', 'due': 'Every Friday', 'class': '12PHYR'},
    {'subject': 'CS Programming', 'due': 'Every Monday', 'class': '12CSP'},
    {'subject': 'CS Theory', 'due': 'Every Wednesday', 'class': '12CST'},
    {'subject': 'Econ', 'due': 'Every Thursday', 'class': '12ECO'},
]

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
    ('64bf7efaed2a47dfb03a6b152e3aef637ac251b68a725a28352f3376ff1384d7', 'Marvelous Marble'),
    ('520c4f511821ced30b99bceafbb02e6b7531e867126b0756e68d5e157691ef2f', 'Arx Lucida'),
    ('315c9e95c567cce4feca78f5ad6e8d08d0a22dac0d56061af567b43eea3d4fa8', 'Koselig'),
    ('a8913b96daceb5b615fe45aad2bb104e04eb7db140242934657111e1d1f55b89', 'Sky Bound'),
    ('66f43b2d2a17f3cee05a127040ca409795058510bd3d1ac7eee224512ec532f5', 'ShardMir'),
    ('fcbba504800751b0fb404a7cd1c9591befdf688ad5451ab2bc1f3651590cc5fc', 'Steinwallburg'),
    ('9ba44e8eafd0158e7e1f63e7d609db308c53f337b79e86bd0b630225451eef34', 'Paradise Palace'),
    ('b3889905b6df31cbe302e58e975988385607771605bf6e8e8e8e31b3d2dc8aa1', 'Sunken Glyphs'),
    ('3cd94552b12fb3a8ac45ca3a5e21a882b71b31c788989b396ab382afc69414ac', 'Grimspyre'),
    ('3125a5f98c3b43cf1e2604e25e8504bffd714ea5843200fa8ddf0b4c58842f16', 'Magenta Mines'),
    ('a2137c20c03ad1848098b47f70417cc0b0bf169010c825dc6fb82f37066808a0', 'Cruising Altitude'),
    ('d03b9f7c10c95f40eed389458be51bdf2437febd5673d028da134e59e503c10b', 'Termite Terror'),
    ('f68a709a296a60f6e6f73a2da670f95aca424be0f2fda5d6b608ece71f339b7c', '4 seasons'),
    ('a1f41dc9e884d5d4b1b6025158d70f0934dc4d892076e6c4b32dc3f3846b882e', 'Lost at sea'),
    ('b430aad5e481caa4588e30f46352b876b62f1ba0cf7730a15efd026c91a8f32e', 'Frosted Fjords'),
    ('95d8f7cbe11053dbdfaeeb2f3c3d8f53f0d45fb6abeb411a74949a4cf52f427f', 'Levitation'),
    ('409f26b9faf55bd0ad748177bf85ebdcfc0ddd572190e7f464f38b4a60587b7e', 'Frozen Ramparts'),
    ('c1a2c5aef1029d7bbf946f08cd087dd25bad6e019a41694a48a0024c27627dc8', 'Tangled Cliffs'),
    ('cad05ca9fb4b1d15b35dc752c3df26d8de422639f65e1041c018b841f641a21a', 'Dinruth'),
    ('9e53d03f4efe86834c49ce202b528d769d9aa7a6e17732d0fc56440463956a1b', 'Sludge Pipe Circuit'),
    ('b77ec520a40c4b38d3d7d653b747b1f8627c98709096568db22cd1bfec534ba6', 'Zealot'),
    ('9f827673c4132828009237a03e12ead73eae87504b4708a79c6cc0858212262d', 'Shrouded Oasis'),
    ('9acd9aef650c4ccc41bb01f72ed44dfaa13f2e4404d2e3466f09cc1adcd9a9c0', 'Cogware'),
    ('62d9989187e4508f7866e7b30aa187ddbee2595df21ff5988d7fec3589f9048d', 'Land of the Rising Run'),
    ('b36162623435dc90a54f57590d2baa9f2d67a51cb12c393531f4b6d5e5528ebf', 'Midas Metropolis'),
    ('74ae56c0f278a19f3b69f3903198c7b9de09981133205856b53bf6bdf8db4211', 'Frozen In Time'),
    ('9f4597449906aa0c2baf9a4737406385c829533e64e9e972b25b4189f4593a54', 'Winterfell'),
    ('28b658c7d10eb8b5de6f465e034e87e40f70b37e4534d8c37d1f2af06b5a36d7', 'Launch Control'),
    ('470af92ed4c0a6f62028d7dea4dbc7765d1db16a3698d6a0c271be582a20a7c6', 'Fractured Shores'),
    ('a6b990137e404c9ef2cb4399c463acbed8ebfa3bb82ab5315027118604c4ec03', 'Starry Tropisx'),
    ('35fe02bf18312713c05528f0b7b8fd15c83dac50bcdcbd373040a16e8bfcc138', 'Flying Dreams'),
    ('18b69f54f119cfb2867abded9a1574f0799a750ef94aa744d9ec8ef6b4d565ae', 'Ghost City'),
    ('5aafb733c264d51b09beedc7bd7eabb5e65bdded338980fcb14ae5ce36955572', 'Asguardia'),
    ('5ea46b3ae268a0196dcc59dabe88926400b56e29814658bfed06a284f837cefd', 'Mos Espa'),
    ('ab8e1c13ddf394102be1cb04adcff8411127f1e7140a216d27a94fc19b7d0428', 'Joenail Jones'),
    ('86335d78d1a06d3dc81d80f84b8ac2e8f6359e9a206826e2c36f7d3f4351bea4', 'Anubis'),
    ('a510bbd3341f2992a12db8a3780cb8943b6087538345d58d16602d6129742df0', 'Natsujo'),
    ('8cf99166f12cbb56a9df4e022a0e9b8c78973adb929dbf1e265ebb9f99f01163', 'Arabica'),
    ('33d99aad2ad5cef45b1d3afb8735c5229cfd98ac7cc24916e0da7283f7a545ce', 'Hyperion\'s Sanctuary'),
    ('5c00f2c90bcf8230183484225d1a417e45b0ad310379acfafd4c8f1dc7345dd7', 'Winter Hollow'),
    ('009fad7fcc215022c6b2dbb2b6de622f07cd88d4930b8e2b6a6b74c1f5de9e44', 'Clay Temples'),
    ('1ad53694ee3e96aea27afa7b64d5c29d115de88a17b69cf3fe3f5609c52b040b', 'Las Calles'),
    ('2ed125037366052871fbb97da6e1bda49cfeb471f6b9c8fa799d520bdb3683e2', 'Desert Stallion'),
    ('f79b1d863d50f9e3b4489988698065c6d775ff3ec90bf91085bad05ad5ec8316', 'Last Remnant'),
    ('27429a1d1bf05770851e3919af70f47c6cd7a269c67032b084fb4345f6c271ce', 'Lu Muvimento'),
    ('f5c327cf09b90e4de8c3c1f9c910dbb7988cf15485d2e4beec3cc03aef408c5c', '90xReset'),
    ('7451c2128cb96bc28195cf0ca0f83a46c3b55d78d434232d9de085dd1cf0ab36', 'Opal Palace - Repolished'),
    ('af6ef508e1f6e47a462a6998b950ef535d1e8a38fe67ead891bf5f2de1346f43', 'Re: Akina'),
    ('089f2aebcfe4f24d8dda3a8a630172d2bd13793e78c5247adfaa760743a377e1', 'Sandline Ultimatum'),
    ('5e40f730509204c77e9c610839ed43addddbe0f8aa007168447f7fde38583905', 'Malformations'),
    ('191737cc4d1b74949e992d99371e5c7f5fc446a716af571c6e5449b23e9f4558', 'Snow Park'),
    ('39bd3fa6c3c769b298c219aee7561af35a6d856bfee14b46b0b48499e7a57ed5', 'concrete jungle'),
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

@app.before_request
def require_login():
    public_endpoints = {'sign_in', 'send_code', 'verify_code', 'static'}
    if request.endpoint not in public_endpoints and 'user_email' not in session:
        return redirect(url_for('sign_in'))

@app.route('/', methods=['GET'])
def sign_in():
    if 'user_email' in session:
        return redirect(url_for('home'))
    return render_template('sign_in.html', email='', success=None, error=None, show_code_field=False)

@app.route('/send-code', methods=['POST'])
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

@app.route('/verify-code', methods=['POST'])
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
    return redirect(url_for('home'))

@app.route('/home')
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

@app.route('/home/add-notice', methods=['POST'])
def add_notice():
    if not can_edit_notices():
        return redirect(url_for('home'))
    title = request.form.get('title', '').strip()
    message = request.form.get('message', '').strip()
    if title and message:
        NOTICES.insert(0, {
            'title': title,
            'message': message,
            'author': session.get('user_email'),
            'created_at': datetime.utcnow().strftime('%b %d %Y %H:%M'),
        })
    return redirect(url_for('home'))

@app.route('/home/add-forum', methods=['POST'])
def add_forum():
    if not can_edit_notices():
        return redirect(url_for('home'))
    subject = request.form.get('subject', '').strip()
    message = request.form.get('message', '').strip()
    if subject and message:
        FORUM_POSTS.insert(0, {
            'subject': subject,
            'message': message,
            'author': session.get('user_email'),
            'created_at': datetime.utcnow().strftime('%b %d %Y %H:%M'),
        })
    return redirect(url_for('home'))

@app.route('/logout')
def logout():
    session.pop('user_email', None)
    return redirect(url_for('sign_in'))

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
        tracks=TRACKS,
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