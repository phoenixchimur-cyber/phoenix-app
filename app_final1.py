from flask import Flask, request, redirect, session
import sqlite3, random, string, qrcode, os, time

app = Flask(__name__)
app.secret_key = "phoenix_secret"
app.permanent_session_lifetime = 1800  # 30 min expiry

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
        points INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending'
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
    body {{font-family:Arial;background:#f2f4f7;margin:0;text-align:center}}
    .box {{background:white;margin:15px;padding:20px;border-radius:12px}}
    input,select {{width:90%;padding:12px;margin:8px;border-radius:8px}}
    button {{width:90%;padding:12px;margin:10px;border:none;border-radius:8px;color:white;font-size:16px}}
    .green{{background:#28a745}} .blue{{background:#007bff}}
    .orange{{background:#ff6600}} .red{{background:#dc3545}} .dark{{background:#333}}
    img.logo {{width:120px;margin-top:10px}}
    </style>

    <script>
    function confirmLogout() {{
        if(confirm("Are you sure you want to logout?")) {{
            window.location.href = "/logout";
        }}
    }}
    </script>

    </head>
    <body>

    <img src="/static/logo.jpg" class="logo">

    {content}

    </body>
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

    <p>📍 Chimur | 📞 7038672255 / 9890072255</p>
    <p>💻 MS-CIT | KLIC | CCTP</p>

    <a href='/join'><button class='green'>Admission</button></a>
    <a href='/login'><button class='blue'>Student Login</button></a>
    <a href='/admin-login'><button class='dark'>Admin</button></a>
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
    <input name='ref' value='{ref}' placeholder='Referral Code'>
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
        return ui("<h3>Already Registered</h3>")

    code=gen_code()

    c.execute("INSERT INTO students VALUES(NULL,?,?,?,?,?,0,'pending')",
              (name,mobile,course,code,ref))

    conn.commit()
    conn.close()

    link=f"{BASE_URL}/join?ref={code}"
    os.makedirs("static", exist_ok=True)
    qrcode.make(link).save(f"static/{code}.png")

    return ui(f"""
    <div class='box'>
    <h3>Admission Submitted</h3>
    <h2>{code}</h2>

    <input id="link" value="{link}">
    <button onclick="copyLink()" class='blue'>Copy Link</button>

    <a href="https://wa.me/?text=Join {link}">
    <button class='green'>Share</button></a>

    <img src="/static/{code}.png" width="200">

    <p>⏳ Points after approval</p>
    </div>

    <script>
    function copyLink(){{
        var copyText=document.getElementById("link");
        copyText.select();
        document.execCommand("copy");
        alert("Copied!");
    }}

    setTimeout(function(){{
        window.open("https://wa.me/?text=Join {link}");
    }},1500);
    </script>
    """)

# ================= LOGIN =================
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
            session.permanent = True
            session['code']=row[0]
            return redirect('/dashboard')

        return ui("<h3>Not Found</h3>")

    return ui("""
    <div class='box'>
    <h2>Student Login</h2>
    <form method='post'>
    <input name='mobile'>
    <button class='blue'>Login</button>
    </form>
    </div>
    """)

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'code' not in session:
        return redirect('/login')

    code=session['code']

    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT name,points,status FROM students WHERE referral_code=?", (code,))
    row=c.fetchone()
    conn.close()

    link=f"{BASE_URL}/join?ref={code}"
    pts = f"{row[1]} Points" if row[2]=="approved" else "⏳ Pending Approval"

    return ui(f"""
    <div class='box'>
    <h2>{row[0]}</h2>
    <h3>{pts}</h3>

    <input value="{link}">
    <a href="https://wa.me/?text=Join {link}">
    <button class='green'>Share</button></a>

    <img src="/static/{code}.png" width="200">

    <button class='red' onclick="confirmLogout()">Logout</button>
    </div>
    """)

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= ADMIN LOGIN =================
@app.route('/admin-login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        if request.form['user']=="admin" and request.form['pass']=="phoenix123":
            session['admin']=True
            return redirect('/admin')
    return ui("""
    <div class='box'>
    <h2>Admin Login</h2>
    <form method='post'>
    <input name='user'>
    <input name='pass' type='password'>
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

    c.execute("SELECT id,name,mobile,status FROM students")
    data=c.fetchall()
    conn.close()

    html=f"""
    <div class='box'>
    <h2>Admin Dashboard</h2>
    <p>Total Students: {total}</p>
    <p>Total Points: {points}</p>

    <button class='red' onclick="confirmLogout()">Logout</button>

    <h3>Student List</h3>
    """

    for d in data:
        html+=f"<p>{d[1]} - {d[2]} ({d[3]})"

        if d[3]=='pending':
            html+=f"<br><a href='/approve/{d[0]}'><button class='green'>Approve</button></a>"
            html+=f"<a href='/reject/{d[0]}'><button class='red'>Reject</button></a>"

        html+="</p><hr>"

    return ui(html+"</div>")

# ================= APPROVE =================
@app.route('/approve/<int:id>')
def approve(id):
    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("SELECT referred_by FROM students WHERE id=?", (id,))
    ref=c.fetchone()[0]

    c.execute("UPDATE students SET status='approved' WHERE id=?", (id,))

    if ref:
        c.execute("UPDATE students SET points=points+50 WHERE referral_code=?", (ref,))

    conn.commit()
    conn.close()

    return redirect('/admin')

# ================= REJECT =================
@app.route('/reject/<int:id>')
def reject(id):
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("DELETE FROM students WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return redirect('/admin')

# ================= RUN =================
if __name__=='__main__':
    import os
    port=int(os.environ.get("PORT",5000))
    app.run(host='0.0.0.0', port=port)