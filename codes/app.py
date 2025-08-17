import ast

from flask import Flask, render_template, request, redirect, url_for, flash, session,jsonify
import sqlite3 # Standard library which allows you to connect DB in python
from chatbot import *
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename
from helper import extract_news_content

import time

app = Flask(__name__)
app.secret_key = "abc"


@app.route('/')
def index():
    is_login = False
    if 'username' in session:
        is_login = True
    return render_template('index.html', is_login = is_login)

@app.route('/api/extract_text', methods=['POST'])
def extract_text_api():
    data = request.get_json()
    url = data.get('link')
    content = extract_news_content(url)
    if content:
        return jsonify({'success': True, 'content': content})
    else:
        return jsonify({'success': False, 'error': 'Failed to extract content' })


@app.route('/create_debate', methods=["GET","POST"])
def create_debate():
    if request.method == "POST": # When user request to create a debate
        topic = request.form.get("topic")
        today = date.today().isoformat()
        with sqlite3.connect('static/database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO debates (topic, date, isClosed) VALUES (?,?,?)
            ''',(topic,today,False))
            conn.commit()
        return redirect(url_for('create_debate'))
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date FROM debates WHERE isClosed = 0 ORDER BY date DESC')
        open_debates = cursor.fetchall()
        cursor.execute('SELECT id, topic, date FROM debates WHERE isClosed = 1 ORDER BY date DESC')
        closed_debates = cursor.fetchall()
    is_admin = session.get("username") == "testtest"

    return render_template('create_debate.html', closed_debates=closed_debates,open_debates=open_debates,is_admin=is_admin)

@app.route('/delete_debate/<int:debate_id>', methods=['POST'])
def delete_debate(debate_id):
    if session.get('username') != 'testtest':
        return redirect(url_for('create_debate'))
    with sqlite3.connect('static/database.db') as conn: # Connectin to DB
        cursor = conn.cursor()
        cursor.execute('DELETE FROM debates WHERE id = ?', (debate_id,))
        conn.commit()
    return redirect(url_for('create_debate'))

@app.route('/close_debate/<int:debate_id>', methods=['POST'])
def close_debate(debate_id):
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE debates SET isClosed = 1 WHERE id = ?', (debate_id,))
        conn.commit()
    return redirect(url_for('create_debate'))

@app.route('/create_news/<int:debate_id>', methods=['GET','POST'])
def create_news(debate_id):
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date, isClosed FROM debates WHERE id = ?', (debate_id,))
        debate = cursor.fetchone()
    if request.method == "POST":  # Adding your news to the db with the summary
        summary = request.form.get('summary')
        link =request.form.get('link')
        title = request.form.get('title')

        content = request.form.get('content')

        classification, percentages, bias_scores = get_bias_classification(content)
        left = bias_scores[0]
        center = bias_scores[1]
        right = bias_scores[2]



        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect('static/database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO news (debate_id,title, link, summary, classification, left, center, right)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (debate_id, title, link, summary, classification, left, center, right))
            conn.commit()
        return redirect(url_for('debate_detail', debate_id=debate_id))

    return render_template('create_news.html', debate=debate)


@app.route('/create_post/<int:debate_id>', methods=['GET','POST'])
def create_post(debate_id):
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date, isClosed FROM debates WHERE id = ?', (debate_id,))
        debate = cursor.fetchone()
    if request.method == "POST": # User request to create a post
        content = request.form.get('content')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect('static/database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO posts (debate_id, username, content, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (debate_id, session['username'], content, timestamp))
            conn.commit()
        return redirect(url_for('debate_detail', debate_id=debate_id))

    return render_template('create_post.html', debate=debate)

@app.route('/debate/<int:debate_id>')
def debate_detail(debate_id):
    user = session.get("username")

    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date, isClosed FROM debates WHERE id = ?', (debate_id,))
        debate = cursor.fetchone()

        cursor.execute('SELECT username, content, timestamp FROM posts WHERE debate_id = ? ORDER BY timestamp DESC', (debate_id,))
        posts = cursor.fetchall()

        cursor.execute('''
            SELECT n.id, n.title, n.link, n.summary, n.classification, n.left, n.center, n.right,
                   EXISTS (
                       SELECT 1 FROM news_votes v WHERE v.news_id = n.id AND v.username = ?
                   ) as has_voted
            FROM news n
            WHERE n.debate_id = ?
            ORDER BY n.id DESC
        ''', (user, debate_id))
        news = cursor.fetchall()

    return render_template('debate_detail.html', debate=debate, posts=posts, news=news)
@app.route('/vote_news/<int:news_id>/<int:debate_id>', methods=["POST"])
def vote_news(news_id, debate_id):
    username = session.get("username")
    if not username:
        return redirect(url_for('login'))

    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()

        # Avoid duplicate votes
        cursor.execute('SELECT 1 FROM news_votes WHERE username = ? AND news_id = ?', (username, news_id))
        if not cursor.fetchone():
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO news_votes (username, news_id, voted_at) VALUES (?, ?, ?)', (username, news_id, now))
            conn.commit()

    return redirect(url_for('debate_detail', debate_id=debate_id))


@app.route('/chatbot')
def chatbot():
    is_login = False
    if 'username' in session:
        is_login = True
    if is_login == False:
        return redirect(url_for('login'))
    return render_template('chatbot.html', is_login = is_login)

@app.route('/profile')
def profile():
    page = 1
    total_pages = 5
    is_login = False
    if 'username' in session:
        is_login = True
    if is_login == False:
        return redirect(url_for('login'))
    conn = sqlite3.connect("static/database.db")
    cursor = conn.cursor()
    command = "SELECT date, question, bias_class, bias_percentage, summary, reason FROM Chatlog where username = ? ORDER BY date DESC LIMIT 5;"
    cursor.execute(command, (session["username"],) )
    recent_classification = cursor.fetchall() # get the results from the above line

    command = "SELECT email FROM Users where username = ?"
    cursor.execute(command, (session["username"], ))
    result = cursor.fetchone() # ("scott@logncoding.com", )
    email = result[0] # "scott@logncoding.com"

    # get all rows
    command = "SELECT * FROM Chatlog where username = ?" # We select every chat(row) from Chatlog
    cursor.execute(command, (session["username"],))
    result = cursor.fetchall()


    total_articles = len(result) # The number of articles that user asked to classify.

    print("Result: ", result) # [ (username,date,question,...keywords), (username,date,question,...keywords), () ]
    keywords = []
    for row in result:
        keywords.append(row[-1])
    print(keywords)

    left_sum = 0
    center_sum = 0
    right_sum = 0
    import ast
    for row in result: # (username, content, X, ,X, bias_class)
        # print(row)
        lst = ast.literal_eval(row[4]) # evealuate string and change it to the list
        left_sum += lst[0]
        center_sum += lst[1]
        right_sum += lst[2]

    left_avg = left_sum  / len(result)
    center_avg = center_sum / len(result)
    right_avg = right_sum / len(result)
    # print(left_avg)
    # print(center_avg)
    # print(right_avg)



    bias_scores = []
    for classification in recent_classification:
        scores = ast.literal_eval(classification[3]) # [20,30,50]
        bias_scores.append(scores)
    print("BIAS SCORE:" , bias_scores)


    conn.close()
    # recent_classification = [ (2025, "news", "right") }, {},{} ]
    return render_template('profile.html',bias_scores=bias_scores,left_avg=left_avg, center_avg=center_avg, right_avg=right_avg, total_articles=total_articles, username = session["username"], is_login = is_login, email=email, recent_classification=recent_classification)


@app.route('/statistics')
def statistics():
    is_login = False
    if 'username' in session:
        is_login = True
    conn = sqlite3.connect('static/database.db')
    cursor = conn.cursor()

    # Fetch recent 7 days chatbot usage
    current_date = datetime.now()
    seven_days_ago = current_date - timedelta(days=7)
    cursor.execute("""
        SELECT Date(date), COUNT(*) 
        FROM Chatlog 
        WHERE Date(date) BETWEEN ? AND ? 
        GROUP BY Date(date) 
        ORDER BY Date(date) ASC;
    """, (seven_days_ago.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d')))
    result = cursor.fetchall()

    # Fetch chatbot usage by month
    cursor.execute("""
        SELECT strftime('%Y-%m', date) AS month, COUNT(*) 
        FROM Chatlog 
        GROUP BY month 
        ORDER BY month ASC;
    """)
    monthly_result = cursor.fetchall()

    # Fetch total users
    cursor.execute("SELECT COUNT(*) FROM Users;")
    total_users = cursor.fetchone()[0]

    # Fetch active users in the last 30 days
    thirty_days_ago = current_date - timedelta(days=30)
    cursor.execute("SELECT COUNT(*) FROM Users WHERE recent_login >= ?", (thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    active_users = cursor.fetchone()[0]

    # Fetch total news and recent news
    cursor.execute("SELECT COUNT(*) FROM Chatlog;")
    total_news = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Chatlog WHERE date >= ?", (thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    recent_news = cursor.fetchone()[0]

    # Fetch top keywords usage
    cursor.execute("""
        SELECT keywords, COUNT(*) FROM Chatlog 
        GROUP BY keywords 
        ORDER BY COUNT(*) DESC 
        LIMIT 10;
    """)
    keyword_result = cursor.fetchall()
    keyword_labels = [row[0] for row in keyword_result]
    keyword_counts = [row[1] for row in keyword_result]

    # Fetch daily user sessions (past 7 days)
    cursor.execute("""
        SELECT Date(recent_login), COUNT(*) 
        FROM Users 
        WHERE Date(recent_login) BETWEEN ? AND ? 
        GROUP BY Date(recent_login) 
        ORDER BY Date(recent_login) ASC;
    """, (seven_days_ago.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d')))
    session_result = cursor.fetchall()
    session_dates = [row[0] for row in session_result]
    session_counts = [row[1] for row in session_result]

    conn.close()

    return render_template('statistics.html',
                           is_login=is_login,
                           recent_news=recent_news,
                           total_news=total_news,
                           active_users=active_users,
                           total_users=total_users,
                           dates=[row[0] for row in result],
                           counts=[row[1] for row in result],
                           months=[row[0] for row in monthly_result],
                           monthly_counts=[row[1] for row in monthly_result],
                           keyword_labels=keyword_labels,
                           keyword_counts=keyword_counts,
                           session_dates=session_dates,
                           session_counts=session_counts)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]
        gender = request.form["gender"]
        age = request.form["age"]
        politics = request.form["politics-side"]
        # country = request.form["country"]
        # race = request.form["race"]
        # religion = request.form["religion"]


        conn = sqlite3.connect('static/database.db')
        cursor = conn.cursor()

        command = "SELECT * FROM Users WHERE username = ?;"
        cursor.execute(command, (username, ))
        result = cursor.fetchone() # (testest,123,adf@gmail.com.)
        if result is None:
            command = "INSERT INTO Users (username, password,email, gender, age,country, race, religion, politics ) VALUES (?,?,?,?,?,?,?,?,?)"
            cursor.execute(command, (username,password,email,gender,age,country,race,religion,politics))
            conn.commit()
            conn.close()
        else: # when user fail to register
            flash('username already exists')
            return render_template('signup.html')


        return redirect(url_for('login'))
    else:
        return render_template('signup.html')

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect('static/database.db')
        cursor = conn.cursor()
        command = "SELECT password FROM Users WHERE username = ?;"
        cursor.execute(command, (username, ))
        result = cursor.fetchone() # (123, )
        if result is None:
            flash('Username or password is wrong')
            return render_template('login.html')
        else:
            password_db = result[0]
            if password == password_db:
                session["username"] = username
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                update_command = "UPDATE Users SET recent_login =? WHERE username =?;"
                cursor.execute(update_command, (current_time, username))
                conn.commit()
                conn.close()
                return redirect(url_for('index'))
            else:
                flash('username or password is wrong')
                return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/upload_pdf', methods = ["POST"])
def read_file():
    file = request.files["pdf_file"]

    filename = secure_filename(file.filename)
    if filename.endswith('.pdf'):
        print("Calling read_pdf")
        text = read_pdf(file)
    else:
        print("Calling docs")
        text = read_docs(file)

    print("Calling get_bias_classification")
    bias_class, bias_score, score_lst = get_bias_classification(text)
    print("Calling reason_news")
    reason = reason_news(text, bias_class)

    summary = summarize_news(text)

    keywords = get_keywords(text)
    #keywords = ",".join(keywords)


    conn = sqlite3.connect('static/database.db')
    cursor = conn.cursor()
    command = "INSERT INTO Chatlog(username, date, question, bias_class, bias_percentage, summary, reason, keywords) Values(?,?,?,?,?,?,?,?)"
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(command, (session["username"], current_date, text, bias_class,str(bias_score), summary, reason,keywords ))
    conn.commit()
    conn.close()

    return jsonify({
        "bias_class": bias_class,
        "left_score": score_lst[0],
        "center_score": score_lst[1],
        "right_score": score_lst[2],
        "keywords": keywords,
        "reason": reason,
        "summary": summary
    })
@app.route('/get_response', methods = ["POST"])
def get_chatbot_response():
    data = request.json
    text = data["message"]
    # response = classify_news(user_input)

    bias_class, bias_score, score_lst = get_bias_classification(text)
    # [left_score, center_score, right_score]
    reason = reason_news(text, bias_class)
    summary = summarize_news(text)

    keywords = get_keywords(text)
    print("ABC", keywords)
    # keywords = ",".join(keywords)

    conn = sqlite3.connect('static/database.db')
    cursor = conn.cursor()
    command = "INSERT INTO Chatlog(username, date, question, bias_class, bias_percentage, summary, reason, keywords) Values(?,?,?,?,?,?,?,?)"
    current_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(command, (session["username"], current_date, text, bias_class,bias_score, summary, reason,keywords ))
    conn.commit()
    conn.close()

    return jsonify({
        "bias_class": bias_class,
        "left_score": score_lst[0],
        "center_score": score_lst[1],
        "right_score": score_lst[2],
        "keywords": keywords,
        "reason": reason,
        "summary": summary
    })

if __name__ =="__main__":
    app.run(debug=True, port = 8080)