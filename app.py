from flask import Flask, request, redirect, session, render_template_string
import sqlite3
import random, string
import qrcode
import os

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
    conn.commit()
    conn.close()

init_db()

# ================= UTIL =================
def gen_code():
    return "PHX" + ''.join(random.choices(string.digits, k=4))

# ================= HOME =================
@app.route('/')
def home():
    return '''
    <h2>🔥 PHOENIX COMPUTER EDUCATION</h2>
    <a href="/join">👉 New Admission</a><br><br>
    <a href="/login">👉 Student Login</a>
    '''

# ================= JOIN =================
@app.route('/join')
def join():
    ref = request.args.get('ref', '')
    return render_template_string('''
    <h2>Admission Form</h2>
    <form method="post" action="/submit">
        Name:<input name="name"><br><br>
        Mobile:<input name="mobile"><br><br>

        Course:
        <select name="course">
            <option>MS-CIT</option>
            <option>KLIC</option>
            <option>CCTP</option>
        </select><br><br>

        Referral Code:<input name="ref" value="{{ref}}"><br><br>

        <button type="submit">Submit</button>
    </form>
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

    # Points system
    if ref:
        c.execute("UPDATE students SET points = points + 50 WHERE referral_code=?", (ref,))

    conn.commit()
    conn.close()

    # QR code generate
    link = f"https://phoenix-app-e92a.onrender.com/join?ref={code}"
    os.makedirs("static", exist_ok=True)
    img = qrcode.make(link)
    img.save(f"static/{code}.png")

    return f"""
    <h3>✅ Admission Successful</h3>
    <p>Your Code: {code}</p>
    <img src="/static/{code}.png"><br>
    <a href="/login">Login Now</a>
    """

# ================= LOGIN =================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        mobile = request.form['mobile']

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT referral_code FROM students WHERE mobile=?", (mobile,))
        row = c.fetchone()
        conn.close()

        if row:
            session['code'] = row[0]
            return redirect('/dashboard')
        else:
            return "❌ Not Found"

    return '''
    <h2>Login</h2>
    <form method="post">
        Mobile:<input name="mobile"><br><br>
        <button>Login</button>
    </form>
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

    link = f"https://phoenix-app-e92a.onrender.com/join?ref={code}"

    return f"""
    <h2>Welcome {row[0]}</h2>
    <p>Points: {row[1]}</p>
    <p>Your Link: {link}</p>
    <img src="/static/{code}.png"><br><br>
    <a href="/redeem">Redeem Reward</a>
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
        return f"🎉 Reward Redeemed: ₹{reward}"
    else:
        conn.close()
        return "❌ Not enough points"

# ================= RUN =================
# ================= REDEEM =================
@app.route('/redeem')
def redeem():
    ...

# 👇👇👇 इथे paste करा 👇👇👇

@app.route('/admin')
def admin():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT name, mobile, course, referral_code, points FROM students")
    data = c.fetchall()

    conn.close()

    html = "<h2>All Students / Logins</h2><table border=1>"
    html += "<tr><th>Name</th><th>Mobile</th><th>Course</th><th>Code</th><th>Points</th></tr>"

    for row in data:
        html += f"<tr><td>{row[0]}</td><td>{row[1]}</td><td>{row[2]}</td><td>{row[3]}</td><td>{row[4]}</td></tr>"

    html += "</table>"
    return html

# ================= RUN =================

if __name__ == '__main__':
    app.run(debug=True)