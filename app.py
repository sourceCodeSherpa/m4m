from flask import Flask, render_template, request, redirect, url_for,  session, flash
import mysql.connector
from config import DB_CONFIG
# 
# Initializing Flask
app = Flask(__name__)
app.secret_key = 'm4m_user_super_secret_key_for_server_to_secure_session_data'
# 
# Connect to the database
def get_db_connection():
    connection = mysql.connector.connect(
        host=DB_CONFIG['host'],
        user=DB_CONFIG['user'],
        password=DB_CONFIG['password'],
        database=DB_CONFIG['database']
    )
    return connection
# 
# Create route for the index page| home page
@app.route("/")
def index():
    return render_template("index.html")
# 
# Route for signing in
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # 1. First check in mentors
        cursor.execute("SELECT * FROM mentors WHERE username = %s AND password = %s", (username, password))
        mentor = cursor.fetchone()

        if mentor:
            session['user_id'] = mentor['id']
            session['role'] = 'mentor'
            flash('Logged in as Mentor!', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('mentor_dashboard'))

        # 2. If not a mentor, check in mentees
        cursor.execute("SELECT * FROM mentees WHERE username = %s AND password = %s", (username, password))
        mentee = cursor.fetchone()

        if mentee:
            session['user_id'] = mentee['id']
            session['role'] = 'mentee'
            flash('Logged in as Mentee!', 'success')
            cursor.close()
            conn.close()
            return redirect(url_for('mentee_dashboard'))

        # 3. If neither, wrong login
        cursor.close()
        conn.close()
        flash('Invalid username or password. Try again.', 'danger')
        return redirect(url_for('index'))
# 
# Route for mentee registration
@app.route('/register_mentee', methods=['GET', 'POST'])
def register_mentee():
    if request.method == 'POST':
        name = request.form['name']
        phone_number = request.form['phone_number']
        interest = request.form['interest']
        
        # Insert into MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mentees (name, phone_number, interests) VALUES (%s, %s, %s)", 
                       (name, phone_number, interest))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('mentee_dashboard'))

    return render_template('register_mentee.html')
# 
# Mentee Dashboard (view mentors)
@app.route('/mentee_dashboard', methods=['GET', 'POST'])
def mentee_dashboard():
    if 'user_id' not in session or session.get('role') != 'mentee':
        flash('You need to sign in as a mentee to access this page.', 'danger')
        return redirect(url_for('index'))

    conn = get_db_connection()

    # Get mentee's interest using dictionary access
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT interest FROM mentees WHERE id = %s", (session['user_id'],))
    mentee = cursor.fetchone()
    cursor.close()

    courses = []

    if mentee:
        interest = mentee['interest']
        
        # Now use a tuple-style cursor for courses (since your HTML template uses index-based access)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM courses WHERE tag = %s", (interest,))
        courses = cursor.fetchall()
        cursor.close()

    conn.close()
    return render_template('mentee_dashboard.html', courses=courses)
# 
# Route for mentor registration
@app.route('/register_mentor', methods=['GET', 'POST'])
def register_mentor():
    if request.method == 'POST':
        name = request.form['name']
        phone_number = request.form['phone_number']
        bio = request.form['bio']
        expertise = request.form['expertise']
        # 
        # Insert into MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mentors (name, phone_number, bio, expertise) VALUES (%s, %s, %s, %s)", 
                       (name, phone_number, bio, expertise))
        conn.commit()
        cursor.close()
        conn.close()

        return redirect(url_for('mentor_dashboard'))

    return render_template('register_mentor.html')
# 
# Mentor Dashboard (view content)
@app.route('/mentor_dashboard', methods=['GET', 'POST'])
def mentor_dashboard():
    # 
    # If user is not validated by session or doesn't have the mentor role, they are redirected
    if 'user_id' not in session or session.get('role') != 'mentor':
        flash('You need to sign in as a mentor to access this page.', 'danger')
        return redirect(url_for('index'))
    conn = get_db_connection()
    cursor = conn.cursor()
    # 
    # Selecting only courses that the logged in user (mentor) has posted
    cursor.execute("SELECT * FROM courses WHERE mentor_id = %s", (session['user_id'],))
    courses = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('mentor_dashboard.html', courses=courses)
# 
# Logout Route
@app.route('/logout')
def logout():
    session.clear()  # Clears all the session data
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))