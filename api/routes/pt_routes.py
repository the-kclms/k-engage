from flask import Blueprint

from api.utils.polytrack_utils import *

pt_blueprint = Blueprint('polytrack', __name__, url_prefix="/polytrack")

@pt_blueprint.route('/')
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

@pt_blueprint.route('/register', methods=['POST'])
def register():
    nickname = request.form.get('nickname', '').strip()
    token_hash = request.form.get('token_hash', '').strip()
    if not nickname or not token_hash:
        return redirect(url_for('polytrack.polytrack_index'))
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
    return redirect(url_for('polytrack.polytrack_index'))

@pt_blueprint.route('/delete/<int:player_id>', methods=['POST'])
def delete_player(player_id):
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM players WHERE id = %s', (player_id,))
        conn.commit()
    finally:
        release_db(conn)
    return redirect(url_for('polytrack.polytrack_index'))