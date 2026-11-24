import os, sqlite3, uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
import jwt
from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('DATABASE_PATH', BASE / 'pinterest.db'))
UPLOAD_DIR = Path(os.environ.get('UPLOAD_FOLDER', BASE / 'static' / 'uploads'))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024
SECRET = os.environ.get('JWT_SECRET_KEY', 'local-development-key-change-before-deploy')
ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def db():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    with db() as con:
        con.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS pins(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), title TEXT NOT NULL, description TEXT DEFAULT '', image TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS saves(user_id INTEGER NOT NULL REFERENCES users(id), pin_id INTEGER NOT NULL REFERENCES pins(id), PRIMARY KEY(user_id,pin_id));''')

def token_user():
    value = request.headers.get('Authorization', '')
    if not value.startswith('Bearer '): return None
    try: return int(jwt.decode(value[7:], SECRET, algorithms=['HS256'])['sub'])
    except (jwt.InvalidTokenError, KeyError, ValueError): return None

def auth_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        uid = token_user()
        if not uid: return jsonify(error='Sign in to continue'), 401
        return fn(uid, *args, **kwargs)
    return wrapped

@app.get('/')
def home(): return render_template('index.html')

@app.get('/uploads/<path:name>')
def uploaded(name): return send_from_directory(UPLOAD_DIR, name)

@app.post('/api/register')
def register():
    data = request.get_json(silent=True) or {}
    username, email, password = (str(data.get(k, '')).strip() for k in ('username','email','password'))
    if len(username)<2 or '@' not in email or len(password)<8: return jsonify(error='Enter a username, valid email, and password of at least 8 characters.'),400
    try:
        with db() as con:
            con.execute('INSERT INTO users(username,email,password) VALUES(?,?,?)',(username,email.lower(),generate_password_hash(password)))
            uid=con.execute('SELECT id FROM users WHERE email=?',(email.lower(),)).fetchone()[0]
    except sqlite3.IntegrityError: return jsonify(error='That username or email is already registered.'),409
    return auth_response(uid,username)

@app.post('/api/login')
def login():
    data=request.get_json(silent=True) or {}
    with db() as con: user=con.execute('SELECT * FROM users WHERE email=?',(str(data.get('email','')).strip().lower(),)).fetchone()
    if not user or not check_password_hash(user['password'],str(data.get('password',''))): return jsonify(error='Email or password is incorrect.'),401
    return auth_response(user['id'],user['username'])

def auth_response(uid,username):
    token=jwt.encode({'sub':str(uid),'exp':datetime.now(timezone.utc)+timedelta(days=7)},SECRET,algorithm='HS256')
    return jsonify(token=token,user={'id':uid,'username':username})

@app.get('/api/pins')
def pins():
    uid=token_user()
    with db() as con:
        rows=con.execute('''SELECT p.*,u.username,(SELECT COUNT(*) FROM saves s WHERE s.pin_id=p.id) saves,
        EXISTS(SELECT 1 FROM saves s WHERE s.pin_id=p.id AND s.user_id=?) saved FROM pins p JOIN users u ON u.id=p.user_id ORDER BY p.id DESC''',(uid or -1,)).fetchall()
    community = [dict(r) for r in rows]
    # Curated inspiration is served as static records so it is immediately
    # searchable and does not require seeded database rows or account IDs.
    try:
        import json
        catalog = json.loads((BASE / 'static' / 'gallery.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        catalog = []
    return jsonify(catalog + community)

@app.post('/api/pins')
@auth_required
def create_pin(uid):
    title=request.form.get('title','').strip(); description=request.form.get('description','').strip(); image=request.files.get('image')
    if not title or not image or not image.filename: return jsonify(error='A title and image are required.'),400
    ext=image.filename.rsplit('.',1)[-1].lower() if '.' in image.filename else ''
    if ext not in ALLOWED: return jsonify(error='Use a PNG, JPG, GIF, or WEBP image.'),400
    filename=secure_filename(f'{uuid.uuid4().hex}.{ext}'); image.save(UPLOAD_DIR/filename)
    with db() as con:
        cur=con.execute('INSERT INTO pins(user_id,title,description,image,created_at) VALUES(?,?,?,?,?)',(uid,title,description,filename,datetime.now(timezone.utc).isoformat()))
        pin_id=cur.lastrowid
    return jsonify(id=pin_id),201

@app.post('/api/pins/<int:pin_id>/save')
@auth_required
def save_pin(uid,pin_id):
    with db() as con:
        if not con.execute('SELECT id FROM pins WHERE id=?',(pin_id,)).fetchone(): return jsonify(error='Pin not found.'),404
        exists=con.execute('SELECT 1 FROM saves WHERE user_id=? AND pin_id=?',(uid,pin_id)).fetchone()
        if exists: con.execute('DELETE FROM saves WHERE user_id=? AND pin_id=?',(uid,pin_id)); saved=False
        else: con.execute('INSERT INTO saves(user_id,pin_id) VALUES(?,?)',(uid,pin_id)); saved=True
    return jsonify(saved=saved)

init_db()
if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=os.environ.get('FLASK_DEBUG')=='1')
