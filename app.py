from flask import Flask, request, redirect, session, render_template_string
import sqlite3
import random, string
import qrcode
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "phoenix_secret"
DB = "phoenix_web.db"

# ================= DATABASE =================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        mobile TEXT,
        course TEXT,
        referral_code TEXT,
        referred_by TEXT,
        points INTEGER DEFAULT 0
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS logins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mobile TEXT,
        time TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ================= UTIL =================
def gen_code():
    return "PHX" + ''.join(random.choices(string.digits, k=4))

BASE_URL = "https://phoenix-app-e92a.onrender.com"

# ================= HOME =================
@app.route('/')
def home():
    return '''
    <div style="text-align:center;font-family:Arial;">
        <h1 style="color:#ff6600;">🔥 PHOENIX COMPUTER EDUCATION</h1>
        <p>Smart Admission & Earn System</p>

        <a href="/join">
            <button style="padding:10px 20px;margin:10px;background:#28a745;color:white;border:none;border-radius:5px;">
                🎓 New Admission
            </button>
        </a><br>

        <a href="/login">
            <button style="padding:10px 20px;margin:10px;background:#007bff;color:white;border:none;border-radius:5px;">
                📱 Student Login
            </button>
        </a><br>

        <a href="/admin-login">
            <button style="padding:10px 20px;margin:10px;background:#333;color:white;border:none;border-radius:5px;">
                🔐 Admin Login
            </button>
        </a>
    </div>
    '''

# ================= JOIN =================
@app.route('/join')
def join():
    ref = request.args.get('ref', '')
    return render_template_string('''
    <div style="max-width:400px;margin:auto;font-family:Arial;">
        <h2 style="text-align:center;color:#ff6600;">Admission Form</h2>

        <form method="post" action="/submit">
            <input name="name" placeholder="Full Name" style="width:100%;padding:10px;margin:5px;"><br>
            <input name="mobile" placeholder="Mobile Number" style="width:100%;padding:10px;margin:5px;"><br>

            <select name="course" style="width:100%;padding:10px;margin:5px;">
                <option>MS-CIT</option>
                <option>KLIC</option>
                <option>CCTP</option>
            </select><br>

            <input name="ref" value="{{ref}}" placeholder="Referral Code" style="width:100%;padding:10px;margin:5px;"><br>

            <button style="width:100%;padding:10px;background:#ff6600;color:white;border:none;border-radius:5px;">
                🚀 Submit Admission
            </button>
        </form>
    </div>
    ''', ref=ref)

# ================= SUBMIT =================
@app.route('/submit', methods=['POST'])
def submit():
    name = request.form['name']
    mobile = request.form['mobile']
    course = request.form['course']
    ref = request.form['ref']

    code = gen_code()

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("INSERT INTO students VALUES (NULL,?,?,?,?,?,0)",
              (name, mobile, course, code, ref))

    if ref:
        c.execute("UPDATE students SET points = points + 50 WHERE referral_code=?", (ref,))

    conn.commit()
    conn.close()

    link = f"{BASE_URL}/join?ref={code}"
    os.makedirs("static", exist_ok=True)
    img = qrcode.make(link)
    img.save(f"static/{code}.png")

    return f"""
    <div style="text-align:center;font-family:Arial;">
        <h3 style="color:green;">✅ Admission Successful</h3>
        <p>Your Code: <b>{code}</b></p>
        <img src="/static/{code}.png"><br><br>
        <a href="/login">
            <button style="padding:10px 20px;background:#007bff;color:white;border:none;border-radius:5px;">
                Login Now
            </button>
        </a>
    </div>
    """

# ================= LOGIN =================
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        mobile = request.form['mobile']

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("SELECT referral_code FROM students WHERE mobile=?", (mobile,))
        row = c.fetchone()

        if row:
            session['code'] = row[0]

            c.execute("INSERT INTO logins VALUES (NULL,?,?)",
                      (mobile, datetime.now().strftime("%Y-%m-%d %H:%M")))

            conn.commit()
            conn.close()

            return redirect('/dashboard')
        else:
            conn.close()
            return "❌ Not Found"

    return '''
    <div style="max-width:400px;margin:auto;text-align:center;font-family:Arial;">
        <h2 style="color:#ff6600;">Student Login</h2>
        <form method="post">
            <input name="mobile" placeholder="Enter Mobile Number"
            style="width:100%;padding:10px;margin:10px;"><br>
            <button style="padding:10px 20px;background:#007bff;color:white;border:none;border-radius:5px;">
                Login
            </button>
        </form>
    </div>
    '''

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    code = session.get('code')
    if not code:
        return redirect('/login')

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT name, points FROM students WHERE referral_code=?", (code,))
    row = c.fetchone()
    conn.close()

    link = f"{BASE_URL}/join?ref={code}"

    return f"""
    <div style="text-align:center;font-family:Arial;">
        <h2 style="color:#ff6600;">Welcome {row[0]}</h2>
        <h3>⭐ Points: {row[1]}</h3>

        <p>Your Referral Link:</p>
        <input value="{link}" style="width:80%;padding:8px;" readonly><br><br>

        <img src="/static/{code}.png"><br><br>

        <a href="/redeem">
            <button style="padding:10px 20px;background:#28a745;color:white;border:none;border-radius:5px;">
                🎁 Redeem Reward
            </button>
        </a>
    </div>
    """

# ================= REDEEM =================
@app.route('/redeem')
def redeem():
    code = session.get('code')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT points FROM students WHERE referral_code=?", (code,))
    pts = c.fetchone()[0]

    if pts >= 100:
        reward = (pts // 100) * 100
        c.execute("UPDATE students SET points = points - ? WHERE referral_code=?", (reward, code))
        conn.commit()
        conn.close()
        return f"<h3 style='color:green;'>🎉 Reward Redeemed: ₹{reward}</h3>"
    else:
        conn.close()
        return "<h3 style='color:red;'>❌ Not enough points</h3>"

# ================= ADMIN =================
ADMIN_USER = "admin"
ADMIN_PASS = "phoenix123"

@app.route('/admin-login', methods=['GET','POST'])
def admin_login():
    if request.method == 'POST':
        if request.form['user'] == ADMIN_USER and request.form['pass'] == ADMIN_PASS:
            session['admin'] = True
            return redirect('/admin')
        else:
            return "❌ Wrong Login"

    return '''
    <h2>Admin Login</h2>
    <form method="post">
    Username:<input name="user"><br><br>
    Password:<input name="pass"><br><br>
    <button>Login</button>
    </form>
    '''

@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin-login')

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    total = c.fetchone()[0]

    c.execute("SELECT SUM(points) FROM students")
    points = c.fetchone()[0] or 0

    c.execute("SELECT name, points FROM students ORDER BY points DESC LIMIT 5")
    top = c.fetchall()

    c.execute("SELECT * FROM students")
    data = c.fetchall()

    conn.close()

    html = f"""
    <h1 style="color:#ff6600;">🔥 ADMIN PANEL</h1>
    <h3>Total Students: {total}</h3>
    <h3>Total Points: {points}</h3>

    <h2>Top Referrers</h2>
    """

    for t in top:
        html += f"<p>{t[0]} - {t[1]}</p>"

    html += "<h2>All Students</h2><table border=1>"

    for d in data:
        html += f"<tr><td>{d[1]}</td><td>{d[2]}</td><td>{d[3]}</td><td>{d[4]}</td><td>{d[6]}</td></tr>"

    html += "</table>"

    return html

# ================= RUN =================
if __name__ == '__main__':
    app.run(debug=True)