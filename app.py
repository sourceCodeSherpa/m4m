from flask import Flask, render_template, request, redirect, url_for,  session, flash, jsonify
import mysql.connector
import os
import africastalking
from config import DB_CONFIG, UPLOAD_FOLDER,AFRICA_TALKING_API_KEY, AFRICA_TALKING_USERNAME
# 
# To store the uploaded and updated timestamps of courses
from datetime import datetime
# 
# Initializing Flask
app = Flask(__name__)
app.secret_key = 'm4m_user_super_secret_key_for_server_to_secure_session_data'
# 
# Initialize the Africa's Talking SDK with your credentials
africastalking.initialize(AFRICA_TALKING_USERNAME, AFRICA_TALKING_API_KEY)
# 
# Accessing the Africa's talking SMS  and airtime API services
sms = africastalking.SMS
airtime = africastalking.Airtime
# 
# Upload path for the thumbnail images
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
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
@app.route("/", methods=["GET", "POST"])
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
        username = request.form['username']
        password = request.form['password']
        bio = request.form['bio']
        interest = request.form['interest']
        phone_number = request.form['phone_number']
        
        # Insert into MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mentees (name, username, password, bio, interest, phone_number) VALUES (%s, %s, %s, %s, %s, %s)", 
                       (name, username, password, bio, interest, phone_number))
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
        username = request.form['username']
        password = request.form['password']
        bio = request.form['bio']
        expertise = request.form['expertise']
        phone_number = request.form['phone_number']
        # 
        # Insert into MySQL
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mentors (name, username, password, bio, expertise, phone_number) VALUES (%s, %s, %s, %s, %s, %s)", 
                       (name, username, password, bio, expertise, phone_number))
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
# 
# Upload Route
@app.route('/upload', methods=["POST", "GET"])
def upload():
    if request.method == 'POST':
        course_name = request.form['course_name']
        description = request.form['description']
        tag = request.form['tag']
        created_at = datetime.now()
        updated_at= datetime.now()
        mentor_id = session['user_id']
        # mentor_id = 
        # 
        # Checking if user uploaded file correctly
        if 'thumbnail' not in request.files:
            return "No file part"
        file = request.files['thumbnail']
        if file.filename == '':
            return "No selected image"
        # 
        # Store|save the file in the designated folder in the server (i.e., static/uploads/)
        file_name = file.filename
        full_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
        file.save(full_path)
        # 
        # Insert into MySQL
        relative_path = f"static/uploads/{file_name}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO courses (name, description, tag, thumbnail_url, created_at, updated_at, mentor_id) VALUES (%s, %s, %s, %s, %s, %s, %s)", 
                       (course_name, description, tag, relative_path, created_at, updated_at, mentor_id))
        # 
        # Send sms to mentees whose interests match the course's tag
        try:
            cursor.execute("SELECT phone_number FROM mentees WHERE interest = %s", (tag,))
            mentees_numbers = cursor.fetchall()

            # Extract phone numbers
            phone_numbers = [row[0] for row in mentees_numbers]

            # Send message
            message = "Hey, there's a new course uploaded for you"
            response = sms.send(message, phone_numbers)
            # 
            # Send airtime to the numbers
            currency_code = "KES"
            amount = 5
            response_2 = airtime.send(phone_number = phone_numbers[0], amount = amount, currency_code = currency_code)

            conn.commit()
            cursor.close()
            conn.close()
            # open_server = jsonify({"sent_to": phone_numbers, "response": response})
            # open_server_2 = jsonify({"sent_to_2": phone_numbers, "response_2": response_2})
            return redirect(url_for('mentor_dashboard'))

        except Exception as e:
            conn.rollback()
            cursor.close()
            conn.close()
            return jsonify({"error": str(e)}), 500

    return render_template("upload.html")
# 
# Delete course option for the mentor
@app.route('/delete_course', methods=['POST', "GET"])
def delete_course():
    if 'user_id' not in session or session.get('role') != 'mentor':
        flash('Unauthorized action.', 'danger')
        return redirect(url_for('index'))

    course_id = request.form['course_id']

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure only the mentor who created the course can delete it
    cursor.execute("DELETE FROM courses WHERE id = %s AND mentor_id = %s", (course_id, session['user_id']))
    conn.commit()
    cursor.close()
    conn.close()

    flash('Course deleted successfully.', 'success')
    return redirect(url_for('mentor_dashboard'))
