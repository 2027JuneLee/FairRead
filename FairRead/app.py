from flask import * #Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
from chatbot import get_response
from datetime import *

app = Flask(__name__)
app.secret_key = "june"

@app.route('/get_response', methods = ["POST"])
def get_chatbot_response():
    data = request.json
    user_input = data["message"]
    response = get_response(user_input)

    conn = sqlite3.connect('static/database.db')
    cursor = conn.cursor()
    command = "INSERT INTO Chatlog (username, date, content, bias) VALUES (?,?,?,?)"

    current_time = datetime.now().strftime('%Y-%m%d %H:%M%S')

    cursor.execute(command, (session["username"], current_time, user_input, response))
    return jsonify({"response": response})

@app.route('/')
def index():
    is_login = False
    if 'username' in session:
        is_login = True
    return render_template('index.html', is_login = is_login)

@app.route('/chatbot')
def chatbot():
    is_login = False
    if 'username' in session:
        is_login = True
    if is_login == False:
        return redirect(url_for('login'))
    return render_template('chatbot.html', is_login = is_login)

@app.route('/statistics')
def statistics():
    return render_template('statistics.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        birthday = request.form['birthday']
        gender = request.form['gender']
        nationality = request.form['nationality']
        race = request.form['race']
        religion = request.form['religion']
        bias = request.form['bias']
        conn = sqlite3.connect("static/database.db")
        cursor = conn.cursor()

        command = "SELECT * FROM users WHERE username = ?;"
        cursor.execute(command, (username,))
        result = cursor.fetchone()

        if result is None:
            command = "INSERT INTO users (username, password, email, birthday, gender, nationality, race, religion, bias) VALUES (?,?,?,?,?,?,?,?,?)"
            cursor.execute(command, (username, password, email, birthday, gender, nationality, race, religion, bias))
            conn.commit()
            conn.close()
        else:
            flash('Username already exists.')
            return render_template('signup.html')

        return redirect(url_for('login'))
    else:
        render_template('signup.html')

    return render_template('signup.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect("static/database.db")
        cursor = conn.cursor()

        command = "SELECT password FROM users WHERE username = ?;"
        cursor.execute(command, (username,))
        result = cursor.fetchone()
        if result is None:
            flash('Incorrect username/password combination')
        else:
            password_db = result[0]
            if password == password_db:
                session['username'] = username
                return redirect(url_for('index'))
            else:
                flash('Incorrect username/password combination')
                return render_template('login.html')

        print(username, password)
    else:
        return render_template('login.html')

if __name__ == "__main__":
    app.run(debug=True, port = 8080)