from flask import Flask, request, redirect, session
import sqlite3, random, string, qrcode, os

app = Flask(__name__)
app.secret_key = "phoenix_secret"
app.permanent_session_lifetime = 1800

DB = "phoenix_web.db"
BASE_URL = "https://phoenix-app-e92a.onrender.com"

# ================= DB =================
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
    input {{width:70%;padding:8px;margin:5px}}
    button {{padding:8px;margin:5px;border:none;border-radius:6px;color:white}}
    .green{{background:#28a745}} .blue{{background:#007bff}}
    .orange{{background:#ff6600}} .red{{background:#dc3545}} .dark{{background:#333}}
    img.logo {{width:120px;margin-top:10px}}
    </style>

    <script>
    function confirmLogout(){{
        if(confirm("Logout?")) window.location='/logout';
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
    <h2>PHOENIX COMPUTER EDUCATION</h2>
    <a href='/join'><button class='green'>Admission</button></a>
    <a href='/login'><button class='blue'>Student Login</button></a>
    <a href='/admin-login'><button class='dark'>Admin</button></a>
    </div>
    """)

# ================= JOIN =================
@app.route('/join')
def join():
    ref=request.args.get('ref','')
    return ui(f"""
    <div class='box'>
    <h2>Admission Form</h2>
    <form method='post' action='/submit'>
    <input name='name' placeholder='Name'><br>
    <input name='mobile' placeholder='Mobile'><br>
    <input name='ref' value='{ref}' placeholder='Referral Code'><br>
    <button class='orange'>Submit</button>
    </form>
    </div>
    """)

# ================= SUBMIT =================
@app.route('/submit', methods=['POST'])
def submit():
    name=request.form['name']
    mobile=request.form['mobile']
    ref=request.form['ref']

    conn=sqlite3.connect(DB)
    c=conn.cursor()

    c.execute("SELECT * FROM students WHERE mobile=?", (mobile,))
    if c.fetchone():
        return ui("Already Registered")

    code=gen_code()

    c.execute("INSERT INTO students VALUES(NULL,?,?,?, ?,?,0,'pending')",
              (name,mobile,"Course",code,ref))

    conn.commit()
    conn.close()

    link=f"{BASE_URL}/join?ref={code}"
    os.makedirs("static", exist_ok=True)
    qrcode.make(link).save(f"static/{code}.png")

    return ui(f"""
    <div class='box'>
    <h3>Submitted</h3>
    <h2>{code}</h2>

    <input id='l' value='{link}'>
    <button onclick='copy()' class='blue'>Copy</button>

    <a href='https://wa.me/?text=Join {link}'>
    <button class='green'>Share</button></a>

    <img src="/static/{code}.png" width="150">

    <script>
    function copy(){{
        var x=document.getElementById('l');
        x.select();document.execCommand('copy');alert("Copied");
    }}
    setTimeout(()=>window.open("https://wa.me/?text=Join {link}"),1500);
    </script>
    </div>
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
            session['code']=row[0]
            return redirect('/dashboard')

    return ui("<form method='post'><input name='mobile'><button class='blue'>Login</button></form>")

# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    code=session.get('code')
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT name,points,status FROM students WHERE referral_code=?", (code,))
    r=c.fetchone()
    conn.close()

    pts = f"{r[1]} Points" if r[2]=="approved" else "Pending Approval"

    return ui(f"""
    <div class='box'>
    <h2>{r[0]}</h2>
    <h3>{pts}</h3>
    <button class='red' onclick='confirmLogout()'>Logout</button>
    </div>
    """)

# ================= ADMIN LOGIN =================
@app.route('/admin-login', methods=['GET','POST'])
def admin_login():
    if request.method=='POST':
        if request.form['user']=="admin" and request.form['pass']=="phoenix123":
            session['admin']=True
            return redirect('/admin')
    return ui("<form method='post'><input name='user'><input name='pass'><button>Login</button></form>")

# ================= EDIT POINT =================
@app.route('/edit/<int:id>', methods=['POST'])
def edit(id):
    pts=int(request.form['points'])
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("UPDATE students SET points=? WHERE id=?", (pts,id))
    conn.commit()
    conn.close()
    return redirect('/admin')

# ================= ADMIN PANEL =================
@app.route('/admin')
def admin():
    if not session.get('admin'):
        return redirect('/admin-login')

    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("SELECT id,name,mobile,points,status FROM students")
    data=c.fetchall()
    conn.close()

    html="<div class='box'><h2>Admin Panel</h2>"

    for d in data:
        html+=f"""
        <p>{d[1]} | {d[2]}<br>
        Points: {d[3]} | {d[4]}</p>

        <form method='post' action='/edit/{d[0]}'>
        <input name='points' placeholder='Edit Points'>
        <button class='blue'>Update</button>
        </form>
        """

        if d[4]=='pending':
            html+=f"""
            <a href='/approve/{d[0]}'><button class='green'>Approve</button></a>
            <a href='/reject/{d[0]}'><button class='red'>Reject</button></a>
            """

        html+="<hr>"

    html+="<button onclick='confirmLogout()' class='red'>Logout</button></div>"
    return ui(html)

# ================= APPROVE =================
@app.route('/approve/<int:id>')
def approve(id):
    conn=sqlite3.connect(DB)
    c=conn.cursor()
    c.execute("UPDATE students SET status='approved' WHERE id=?", (id,))
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

# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

# ================= RUN =================
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)