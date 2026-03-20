from flask import Flask, request, redirect, session
import sqlite3, random, string, qrcode, os

app = Flask(__name__)
app.secret_key = "phoenix_secret"
DB = "phoenix_web.db"
BASE_URL = "https://phoenix-app-e92a.onrender.com"

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

# ================= UI =================
def ui(content):
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {{font-family:Arial;background:#f2f4f7;margin:0}}
    .box {{background:white;margin:15px;padding:20px;border-radius:12px;text-align:center}}
    input,select {{width:90%;padding:12px;margin:8px;border-radius:8px}}
    button {{width:90%;padding:12px;margin:10px;border:none;border-radius:8px;color:white;font-size:16px}}
    .green{{background:#28a745}}
    .blue{{background:#007bff}}
    .orange{{background:#ff6600}}
    .dark{{background:#333}}
    </style>
    </head>
    <body>{content}</body>
    </html>
    """

def gen_code():
    return "PHX" + ''.join(random.choices(string.digits, k=4))

# ================= HOME =================
@app.route('/')
def home():
    return ui("""
    <div class='box'>
    <h2>🔥 PHOENIX COMPUTER EDUCATION</h2>

    <a href='/join'><button class='green'>🎓 Admission</button></a>
    <a href='/login'><button class='blue'>📱 Student Login</button></a>
    <a href='/admin-login'><button class='dark'>🔐 Admin Login</button></a>
    <a href='/leaderboard'><button class='orange'>🏆 Leaderboard</button></a>
    </div>
    """)

# ================= JOIN =================
@app.route('/join')
def join():
    ref = request.args.get('ref','')
    return ui(f"""
    <div class='box'>
    <h2>Admission Form</h2>
    <form method='post' action='/submit'>
    <input name='name' placeholder='Full Name'>
    <input name='mobile' placeholder='Mobile'>
    <select name='course'>
    <option>MS-CIT</option><option>KLIC</option><option>CCTP</option>
    </select>
    <input name='ref' value='{ref}' placeholder='Referral Code (Optional)'>
    <button class='orange'>Submit</button>
    </form>
    </div>
    """)

# ================= SUBMIT =================
@app.route('/submit', methods=['POST'])
def submit():
    name=request.form['name']
    mobile=request.form['mobile']
    course=request.form['course']
    ref=request.form['ref']

    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("SELECT * FROM students WHERE mobile=?", (mobile,))
    if c.fetchone():
        return ui("<h3>❌ Already Registered</h3>")

    if ref:
        c.execute("SELECT * FROM students WHERE referral_code=?", (ref,))
        if not c.fetchone():
            return ui("<h3>❌ Invalid Referral Code</h3>")

    code=gen_code()

    c.execute("INSERT INTO students VALUES(NULL,?,?,?,?,?,0)",
              (name,mobile,course,code,ref))

    if ref:
        c.execute("UPDATE students SET points=points+50 WHERE referral_code=?", (ref,))

    conn.commit()
    conn.close()

    link=f"{BASE_URL}/join?ref={code}"
    os.makedirs("static", exist_ok=True)
    qrcode.make(link).save(f"static/{code}.png")

    return ui(f"""
    <div class='box'>
    <h3>✅ Admission Successful</h3>
    <p>Your Code: {code}</p>
    <img src="/static/{code}.png"><br>
    <a href='/login'><button class='blue'>Login</button></a>
    </div>
    """)

# ================= STUDENT LOGIN =================
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        mobile=request.form['mobile']
        conn=sqlite3.connect(DB)
        c=conn.cursor()
        c.execute("SELECT referral_code FROM students WHERE mobile=?", (mobile,))
        row=c.fetchone()
        conn.close()

        if row:
            session['code']=row[0]
            return redirect('/dashboard')

        return ui("<div class='box'><h3 style='color:red;'>❌ Student Not Found</h3></div>")

    return ui("""
    <div class='box'>
    <h2 style='color:#ff6600;'>📱 Student Login</h2>
    <form method='post'>
    <input name='mobile' placeholder='Enter Mobile Number'>
    <button class='blue'>Login</button>
    </form>
    </div>
    """)

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    code=session.get('code')
    if not code:
        return redirect('/login')

    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT name,points FROM students WHERE referral_code=?", (code,))
    row=c.fetchone()
    conn.close()

    link=f"{BASE_URL}/join?ref={code}"

    return ui(f"""
    <div class='box'>
    <h2>{row[0]}</h2>
    <h3>⭐ {row[1]} Points</h3>

    <input value="{link}" readonly>

    <a href="https://wa.me/?text=Join Phoenix 🚀 {link}">
    <button class='green'>📲 Share</button></a>

    <img src="/static/{code}.png" width="200"><br>

    <a href='/leaderboard'><button class='orange'>🏆 Leaderboard</button></a>
    <a href='/redeem'><button class='green'>🎁 Redeem</button></a>
    </div>
    """)

# ================= REDEEM =================
@app.route('/redeem')
def redeem():
    code=session.get('code')
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT points FROM students WHERE referral_code=?", (code,))
    pts=c.fetchone()[0]

    if pts>=100:
        reward=(pts//100)*100
        c.execute("UPDATE students SET points=points-? WHERE referral_code=?", (reward,code))
        conn.commit()
        return ui(f"<h2>🎉 Redeemed {reward}</h2>")

    return ui("<h2>❌ Not enough points</h2>")

# ================= LEADERBOARD =================
@app.route('/leaderboard')
def leaderboard():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT name,points FROM students ORDER BY points DESC LIMIT 10")
    data=c.fetchall()
    conn.close()

    html="<div class='box'><h2>🏆 Top Referrers</h2>"
    r=1
    for d in data:
        html+=f"<p>{r}. {d[0]} - {d[1]} pts</p>"
        r+=1

    return ui(html+"</div>")

# ================= ADMIN LOGIN =================
ADMIN_USER="admin"
ADMIN_PASS="phoenix123"

@app.route('/admin-login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        if request.form['user']==ADMIN_USER and request.form['pass']==ADMIN_PASS:
            session['admin']=True
            return redirect('/admin')
        return ui("<h3>❌ Wrong Login</h3>")

    return ui("""
    <div class='box'>
    <h2>🔐 Admin Login</h2>
    <form method='post'>
    <input name='user' placeholder='Username'>
    <input name='pass' type='password' placeholder='Password'>
    <button class='dark'>Login</button>
    </form>
    </div>
    """)

# ================= ADMIN PANEL =================
@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin-login')

    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("SELECT COUNT(*) FROM students")
    total=c.fetchone()[0]

    c.execute("SELECT SUM(points) FROM students")
    points=c.fetchone()[0] or 0

    c.execute("SELECT name,points FROM students ORDER BY points DESC LIMIT 5")
    top=c.fetchall()

    conn.close()

    html=f"""
    <div class='box'>
    <h2>🔥 Admin Dashboard</h2>
    <p>Total Students: {total}</p>
    <p>Total Points: {points}</p>
    <h3>Top Referrers</h3>
    """

    for t in top:
        html+=f"<p>{t[0]} - {t[1]} pts</p>"

    html+="</div>"
    return ui(html)

# ================= RUN =================
if __name__=='__main__':
    app.run(debug=True)