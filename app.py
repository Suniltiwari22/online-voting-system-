# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
import random
import string
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DATABASE = 'voting.db'

def get_db_connection():
    """Create a database connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """Create tables in the database if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            aadhar TEXT NOT NULL,
            pan TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            phone TEXT NOT NULL,
            has_voted INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS votes (
            party TEXT NOT NULL,
            count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        aadhar = request.form['aadhar']
        pan = request.form['pan']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        phone = request.form['phone']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (name, aadhar, pan, email, password, phone) VALUES (?, ?, ?, ?, ?, ?)',
                           (name, aadhar, pan, email, password, phone))
            conn.commit()
        except sqlite3.IntegrityError:
            # If the email is already registered
            return render_template('signup.html', error="Email already registered. Please use a different email.")

        conn.close()
        return redirect(url_for('signin'))
    return render_template('signup.html')

@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['phone'] = user['phone']
            return redirect(url_for('dashboard'))
        else:
            return render_template('signin.html', error="Invalid email or password. Please try again.")

    return render_template('signin.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('signin'))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        party = request.form['party']
        user_id = session['user_id']

        cursor.execute('SELECT has_voted FROM users WHERE id = ?', (user_id,))
        has_voted = cursor.fetchone()['has_voted']

        if has_voted:
            return render_template('dashboard.html', user=session, error="You have already voted. You cannot vote again.")

        # Update the vote count
        cursor.execute('SELECT count FROM votes WHERE party = ?', (party,))
        result = cursor.fetchone()

        if result:
            cursor.execute('UPDATE votes SET count = count + 1 WHERE party = ?', (party,))
        else:
            cursor.execute('INSERT INTO votes (party, count) VALUES (?, ?)', (party, 1))

        # Mark user as having voted
        cursor.execute('UPDATE users SET has_voted = 1 WHERE id = ?', (user_id,))

        conn.commit()
        conn.close()

        return render_template('dashboard.html', user=session, success="Your vote has been counted successfully!")

    # Fetch user details and available parties for voting
    parties = ['BJP', 'Congress', 'SP', 'BSP']
    return render_template('dashboard.html', user=session, parties=parties)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == 'admin' and password == '1234':
            session['admin_logged_in'] = True
            return redirect(url_for('results'))
        else:
            return render_template('admin.html', error="Invalid admin credentials. Please try again.")

    return render_template('admin.html')

@app.route('/results')
def results():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM votes')
    votes = cursor.fetchall()
    conn.close()

    # Calculate total votes and percentages
    total_votes = sum([vote['count'] for vote in votes])
    vote_percentages = [(vote['party'], vote['count'], (vote['count'] / total_votes) * 100 if total_votes > 0 else 0) for vote in votes]

    return render_template('results.html', votes=vote_percentages, total_votes=total_votes)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    create_tables()  # Ensure the database and tables are created before running the app
    app.run(debug=True)
