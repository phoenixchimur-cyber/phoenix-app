from flask import Flask, request, redirect, session
import sqlite3, random, string, qrcode, os
from datetime import datetime

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

    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        time TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ================= UI =================
def ui(content):
    return f"""
    <html>
    <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
    body {{font-family:Arial;background:#f2f4f7;margin:0}}
    .box {{background:white;margin:15px;padding:20px;border-radius:12px;text-align:center}}
    input,select {{width:90%;padding:12px;margin:8px;border-radius:8px}}
    button {{width:90%;padding:12px;margin:10px;border:none;border-radius:8px;color:white}}
    .green{{background:#28a745}} .blue{{background:#007bff}} .orange{{background:#ff6600}}
    </style>
    </head>
    <body>{content}</body></html>
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
    <a href='/login'><button class='blue'>📱 Login</button></a>
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

    # Duplicate check
    c.execute("SELECT * FROM students WHERE mobile=?", (mobile,))
    if c.fetchone():
        return ui("<h3>❌ Already Registered</h3>")

    # Referral validation
    if ref:
        c.execute("SELECT * FROM students WHERE referral_code=?", (ref,))
        if not c.fetchone():
            return ui("<h3>❌ Invalid Referral Code</h3>")

    code=gen_code()

    c.execute("INSERT INTO students VALUES(NULL,?,?,?,?,?,0)",
              (name,mobile,course,code,ref))

    if ref:
        c.execute("UPDATE students SET points=points+50 WHERE referral_code=?", (ref,))

    # AI alert
    if ref == "":
        c.execute("INSERT INTO alerts VALUES(NULL,?,?)",
                  ("No referral used", datetime.now().strftime("%Y-%m-%d %H:%M")))

    conn.commit()
    conn.close()

    link=f"{BASE_URL}/join?ref={code}"
    os.makedirs("static", exist_ok=True)
    qrcode.make(link).save(f"static/{code}.png")

    return ui(f"<h3>✅ Done<br>{code}</h3><img src='/static/{code}.png'>")

# ================= LOGIN =================
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        mobile=request.form['mobile']
        conn=sqlite3.connect(DB)
        c=conn.cursor()
        c.execute("SELECT referral_code FROM students WHERE mobile=?", (mobile,))
        row=c.fetchone()
        if row:
            session['code']=row[0]
            return redirect('/dashboard')
        return ui("❌ Not Found")

    return ui("<form method='post'><input name='mobile'><button class='blue'>Login</button></form>")

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    code=session.get('code')
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT name,points FROM students WHERE referral_code=?", (code,))
    row=c.fetchone()
    link=f"{BASE_URL}/join?ref={code}"

    return ui(f"""
    <div class='box'>
    <h2>{row[0]}</h2>
    <h3>{row[1]} Points</h3>
    <input value="{link}">
    <a href="https://wa.me/?text=Join {link}">
    <button class='green'>Share</button></a>
    <img src="/static/{code}.png" width="200">
    <a href='/leaderboard'><button>Leaderboard</button></a>
    <a href='/redeem'><button class='green'>Redeem</button></a>
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
        return ui(f"🎉 Redeemed {reward}")
    return ui("❌ Not enough")

# ================= LEADERBOARD =================
@app.route('/leaderboard')
def leaderboard():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT name,points FROM students ORDER BY points DESC LIMIT 10")
    data=c.fetchall()
    html="<div class='box'><h2>Top Referrers</h2>"
    r=1
    for d in data:
        html+=f"<p>{r}. {d[0]} - {d[1]}</p>"; r+=1
    return ui(html+"</div>")

# ================= ALERTS =================
@app.route('/alerts')
def alerts():
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT * FROM alerts")
    data=c.fetchall()
    html="<div class='box'><h2>AI Alerts</h2>"
    for d in data:
        html+=f"<p>{d[1]}</p>"
    return ui(html+"</div>")

# ================= RUN =================
if __name__=='__main__':
    app.run(debug=True)