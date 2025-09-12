import ast
from collections import Counter

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
import sqlite3
from chatbot import *
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename
from helper import extract_news_content
from zoneinfo import ZoneInfo
import time

app = Flask(__name__)
app.config['APP_TZ'] = ZoneInfo("Asia/Seoul")
app.secret_key = "abc"

def now_kst():
    return datetime.now(app.config['APP_TZ'])

def current_user():
    return session.get("username")

def is_admin_user():
    return current_user() == "testtest"

@app.route('/')
def index():
    is_login = 'username' in session
    return render_template('index.html', is_login=is_login, is_admin=is_admin_user())

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
    is_login = 'username' in session
    if request.method == "POST":
        topic = request.form.get("topic")
        today = now_kst().date().isoformat()
        with sqlite3.connect('static/database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO debates (topic, date, isClosed) VALUES (?,?,?)',
                           (topic, today, False))
            conn.commit()
        return redirect(url_for('create_debate'))

    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date FROM debates WHERE isClosed = 0 ORDER BY date DESC')
        open_debates = cursor.fetchall()
        cursor.execute('SELECT id, topic, date FROM debates WHERE isClosed = 1 ORDER BY date DESC')
        closed_debates = cursor.fetchall()

    is_admin = session.get("username") == "testtest"
    return render_template('create_debate.html',
                           is_login=is_login,
                           closed_debates=closed_debates,
                           open_debates=open_debates,
                           is_admin=is_admin)

@app.route('/delete_debate/<int:debate_id>', methods=['POST'])
def delete_debate(debate_id):
    if session.get('username') != 'testtest':
        return redirect(url_for('create_debate'))
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM debates WHERE id = ?', (debate_id,))
        conn.commit()
    return redirect(url_for('create_debate'))

@app.route('/delete_post/<int:post_id>/<int:debate_id>', methods=['POST'])
def delete_post(post_id, debate_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))

    with sqlite3.connect('static/database.db') as conn:
        c = conn.cursor()
        c.execute('SELECT username FROM posts WHERE id = ?', (post_id,))
        row = c.fetchone()
        if not row:
            return redirect(url_for('debate_detail', debate_id=debate_id))
        author = row[0]

        is_admin = (username == 'testtest')
        if not (is_admin or username == author):
            abort(403)

        c.execute('DELETE FROM post_comments WHERE post_id = ?', (post_id,))
        c.execute('DELETE FROM post_likes    WHERE post_id = ?', (post_id,))
        c.execute('DELETE FROM posts         WHERE id = ?', (post_id,))
        conn.commit()

    return redirect(url_for('debate_detail', debate_id=debate_id))

@app.route('/delete_news/<int:news_id>/<int:debate_id>', methods=['POST'])
def delete_news(news_id, debate_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    if username != 'testtest':
        abort(403)

    with sqlite3.connect('static/database.db') as conn:
        c = conn.cursor()
        c.execute('DELETE FROM news_votes WHERE news_id = ?', (news_id,))
        c.execute('DELETE FROM news       WHERE id = ?', (news_id,))
        conn.commit()

    return redirect(url_for('debate_detail', debate_id=debate_id))

@app.route('/close_debate/<int:debate_id>', methods=['POST'])
def close_debate(debate_id):
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE debates SET isClosed = 1 WHERE id = ?', (debate_id,))
        conn.commit()
    return redirect(url_for('create_debate'))

@app.route('/create_news/<int:debate_id>', methods=['GET','POST'])
def create_news(debate_id):
    is_login = 'username' in session
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date, isClosed FROM debates WHERE id = ?', (debate_id,))
        debate = cursor.fetchone()

    if request.method == "POST":
        summary = request.form.get('summary')
        link = request.form.get('link')
        title = request.form.get('title')
        content = request.form.get('content')

        classification, percentages, bias_scores = get_bias_classification(content)
        left, center, right = bias_scores

        timestamp = now_kst().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect('static/database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO news (debate_id,title, link, summary, classification, left, center, right)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (debate_id, title, link, summary, classification, left, center, right))
            conn.commit()
        return redirect(url_for('debate_detail', debate_id=debate_id))

    return render_template('create_news.html',
                           is_login=is_login,
                           is_admin=is_admin_user(),
                           debate=debate)

@app.route('/create_post/<int:debate_id>', methods=['GET','POST'])
def create_post(debate_id):
    is_login = 'username' in session
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date, isClosed FROM debates WHERE id = ?', (debate_id,))
        debate = cursor.fetchone()

    if request.method == "POST":
        content = request.form.get('content')
        timestamp = now_kst().strftime('%Y-%m-%d %H:%M:%S')
        with sqlite3.connect('static/database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO posts (debate_id, username, content, timestamp)
                VALUES (?, ?, ?, ?)
            ''', (debate_id, session['username'], content, timestamp))
            conn.commit()
        return redirect(url_for('debate_detail', debate_id=debate_id))

    return render_template('create_post.html',
                           is_login=is_login,
                           is_admin=is_admin_user(),
                           debate=debate)

@app.route('/debate/<int:debate_id>')
def debate_detail(debate_id):
    user = session.get("username")
    is_login = 'username' in session
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT id, topic, date, isClosed FROM debates WHERE id = ?', (debate_id,))
        debate = cursor.fetchone()

        cursor.execute('SELECT id, username, content, timestamp FROM posts WHERE debate_id = ? ORDER BY timestamp DESC', (debate_id,))
        posts = cursor.fetchall()

        cursor.execute('SELECT post_id, COUNT(*) FROM post_likes GROUP BY post_id')
        likes_dict = dict(cursor.fetchall())

        cursor.execute('SELECT post_id,username,comment,timestamp FROM post_comments ORDER BY timestamp ASC')
        all_comments = cursor.fetchall()
        comments_dict = {}
        for post_id, username, comment, timestamp in all_comments:
            comments_dict.setdefault(post_id, []).append((username, comment, timestamp))

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

    is_admin = (user == "testtest")
    return render_template('debate_detail.html',
                           debate=debate,
                           posts=posts,
                           news=news,
                           likes_dict=likes_dict,
                           comments_dict=comments_dict,
                           current_user=user,
                           is_login=is_login,
                           is_admin=is_admin)

@app.route('/like_post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM post_likes WHERE post_id = ? AND username = ?', (post_id, username))
        if not cursor.fetchone():
            cursor.execute('INSERT INTO post_likes (post_id, username, timestamp) VALUES (?, ?, ?)',
                           (post_id, username, now_kst().strftime('%Y-%m-%d %H:%M:%S')))
            conn.commit()
        else:
            cursor.execute('DELETE FROM post_likes WHERE post_id = ? AND username = ?', (post_id, username))
            conn.commit()

        cursor.execute('SELECT debate_id FROM posts WHERE id = ?', (post_id,))
        debate_id = cursor.fetchone()[0]
    return redirect(url_for('debate_detail', debate_id=debate_id))

@app.route('/comment_post/<int:post_id>', methods=['POST'])
def comment_post(post_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
    comment = request.form.get('comment')
    if comment:
        with sqlite3.connect('static/database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO post_comments (post_id, username, comment, timestamp) VALUES (?, ?, ?, ?)',
                           (post_id, username, comment, now_kst().strftime('%Y-%m-%d %H:%M:%S')))
            cursor.execute('SELECT debate_id FROM posts WHERE id = ?', (post_id,))
            debate_id = cursor.fetchone()[0]
    return redirect(url_for('debate_detail', debate_id=debate_id))

@app.route('/vote_news/<int:news_id>/<int:debate_id>', methods=["POST"])
def vote_news(news_id, debate_id):
    username = session.get("username")
    if not username:
        return redirect(url_for('login'))

    with sqlite3.connect('static/database.db') as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM news_votes WHERE username = ? AND news_id = ?', (username, news_id))
        if not cursor.fetchone():
            now = now_kst().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('INSERT INTO news_votes (username, news_id, voted_at) VALUES (?, ?, ?)',
                           (username, news_id, now))
            conn.commit()

    return redirect(url_for('debate_detail', debate_id=debate_id))

@app.route('/chatbot')
def chatbot():
    is_login = 'username' in session
    if not is_login:
        return redirect(url_for('login'))
    return render_template('chatbot.html', is_login=is_login, is_admin=is_admin_user())

@app.route('/profile')
def profile():
    is_login = 'username' in session
    if not is_login:
        return redirect(url_for('login'))

    conn = sqlite3.connect("static/database.db")
    cursor = conn.cursor()

    cursor.execute("""
        SELECT date, question, bias_class, bias_percentage, summary, reason
        FROM Chatlog
        WHERE username = ?
        ORDER BY date DESC
        LIMIT 5;
    """, (session["username"],))
    recent_classification = cursor.fetchall()

    cursor.execute("SELECT email FROM Users WHERE username = ?;", (session["username"],))
    email_row = cursor.fetchone()
    email = email_row[0] if email_row and email_row[0] else ""

    cursor.execute("SELECT * FROM Chatlog WHERE username = ?;", (session["username"],))
    rows = cursor.fetchall()
    conn.close()

    total_articles = len(rows)
    left_avg = center_avg = right_avg = 0.0
    bias_scores = []

    def safe_parse_scores(x):
        try:
            val = ast.literal_eval(x) if isinstance(x, str) else x
            if isinstance(val, (list, tuple)) and len(val) == 3 and all(isinstance(n, (int, float)) for n in val):
                return [float(val[0]), float(val[1]), float(val[2])]
        except Exception:
            pass
        return None

    if total_articles > 0:
        L = C = R = 0.0
        valid_count = 0
        for row in rows:
            scores = safe_parse_scores(row[4])
            if scores:
                L += scores[0]; C += scores[1]; R += scores[2]
                valid_count += 1
        if valid_count > 0:
            left_avg = L / valid_count
            center_avg = C / valid_count
            right_avg = R / valid_count

    for classification in recent_classification:
        scores = safe_parse_scores(classification[3])
        bias_scores.append(scores if scores else [0, 0, 0])

    return render_template('profile.html',
                           bias_scores=bias_scores,
                           left_avg=left_avg, center_avg=center_avg, right_avg=right_avg,
                           total_articles=total_articles,
                           username=session["username"],
                           is_login=is_login,
                           is_admin=is_admin_user(),
                           email=email,
                           recent_classification=recent_classification)

@app.route('/statistics')
def statistics():
    if not is_admin_user():
        return redirect(url_for('index'))
    is_login = 'username' in session

    conn = sqlite3.connect('static/database.db')
    cursor = conn.cursor()

    current_date = now_kst()
    seven_days_ago = current_date - timedelta(days=7)

    # Recent 7-day chatbot usage
    cursor.execute("""
        SELECT Date(date), COUNT(*)
        FROM Chatlog
        WHERE Date(date) BETWEEN ? AND ?
        GROUP BY Date(date)
        ORDER BY Date(date) ASC;
    """, (seven_days_ago.strftime('%Y-%m-%d'), current_date.strftime('%Y-%m-%d')))
    result = cursor.fetchall()

    # Monthly usage
    cursor.execute("""
        SELECT strftime('%Y-%m', date) AS month, COUNT(*)
        FROM Chatlog
        GROUP BY month
        ORDER BY month ASC;
    """)
    monthly_result = cursor.fetchall()

    # Totals
    cursor.execute("SELECT COUNT(*) FROM Users;")
    total_users = cursor.fetchone()[0]

    thirty_days_ago = current_date - timedelta(days=30)
    cursor.execute("SELECT COUNT(*) FROM Users WHERE recent_login >= ?",
                   (thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    active_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Chatlog;")
    total_news = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM Chatlog WHERE date >= ?",
                   (thirty_days_ago.strftime('%Y-%m-%d %H:%M:%S'),))
    recent_news = cursor.fetchone()[0]

    # --- Top keywords (frequency only) ---
    cursor.execute("SELECT keywords FROM Chatlog;")
    rows = cursor.fetchall()
    counter = Counter()
    for (kw_raw,) in rows:
        if not kw_raw: continue
        try:
            parsed = ast.literal_eval(kw_raw) if isinstance(kw_raw, str) else kw_raw
            items = list(parsed) if isinstance(parsed, (list, tuple, set)) else [str(parsed)]
        except Exception:
            items = [str(kw_raw)]
        flattened = []
        for it in items:
            if isinstance(it, str):
                flattened.extend([s.strip() for s in it.split(',') if s.strip()])
        for token in flattened:
            counter[token] += 1

    top_keywords = counter.most_common(20)
    keyword_labels = [k for k, _ in top_keywords]
    keyword_counts = [v for _, v in top_keywords]

    # --- Bias aggregates: overall + per keyword (for toggle) ---
    cursor.execute("SELECT bias_percentage, keywords FROM Chatlog;")
    bias_rows = cursor.fetchall()

    def parse_scores(x):
        try:
            v = ast.literal_eval(x) if isinstance(x, str) else x
            if isinstance(v, (list, tuple)) and len(v) == 3:
                return float(v[0]), float(v[1]), float(v[2])
        except Exception:
            pass
        return None

    def tokenize_keywords(kw_raw):
        if not kw_raw:
            return []
        try:
            parsed = ast.literal_eval(kw_raw) if isinstance(kw_raw, str) else kw_raw
            items = list(parsed) if isinstance(parsed, (list, tuple, set)) else [str(parsed)]
        except Exception:
            items = [str(kw_raw)]
        tokens = []
        for it in items:
            if isinstance(it, str):
                tokens.extend([s.strip() for s in it.split(',') if s.strip()])
        return tokens

    tl = tc = tr = 0.0
    n = 0
    by_kw = {}  # kw -> [sumL, sumC, sumR, count]

    for bias_raw, kw_raw in bias_rows:
        s = parse_scores(bias_raw)
        if not s:
            continue
        l, c, r = s
        tl += l; tc += c; tr += r; n += 1

        for tok in set(tokenize_keywords(kw_raw)):
            agg = by_kw.setdefault(tok, [0.0, 0.0, 0.0, 0])
            agg[0] += l; agg[1] += c; agg[2] += r; agg[3] += 1

    bias_all = [
        round(tl / n, 2) if n else 0.0,
        round(tc / n, 2) if n else 0.0,
        round(tr / n, 2) if n else 0.0,
    ]
    bias_by_keyword = {
        k: [ round(s[0]/s[3], 2), round(s[1]/s[3], 2), round(s[2]/s[3], 2) ]
        for k, s in by_kw.items() if s[3] > 0
    }

    # Sessions (past 7 days)
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
                           is_admin=is_admin_user(),
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
                           session_counts=session_counts,
                           bias_all=bias_all,
                           bias_by_keyword=bias_by_keyword)

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

        conn = sqlite3.connect('static/database.db')
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM Users WHERE username = ?;", (username,))
        exists = cursor.fetchone()
        if exists:
            conn.close()
            flash('username already exists')
            return render_template('signup.html')

        cursor.execute(
            "INSERT INTO Users (username, password, email, gender, age) VALUES (?,?,?,?,?)",
            (username, password, email, gender, age)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('register', registered=1))

    registered = request.args.get('registered') == '1'
    return render_template('signup.html', registered=registered)

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        conn = sqlite3.connect('static/database.db')
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM Users WHERE username = ?;", (username,))
        result = cursor.fetchone()
        if result is None:
            flash('Username or password is wrong')
            return render_template('login.html')
        else:
            password_db = result[0]
            if password == password_db:
                session["username"] = username
                current_time = now_kst().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("UPDATE Users SET recent_login = ? WHERE username = ?;",
                               (current_time, username))
                conn.commit()
                conn.close()
                return redirect(url_for('index'))
            else:
                flash('username or password is wrong')
                return render_template('login.html')
    else:
        return render_template('login.html')

@app.route('/upload_pdf', methods=["POST"])
def read_file():
    file = request.files["pdf_file"]
    filename = secure_filename(file.filename)
    if filename.endswith('.pdf'):
        text = read_pdf(file)
    else:
        text = read_docs(file)

    bias_class, bias_score, score_lst = get_bias_classification(text)
    reason = reason_news(text, bias_class)
    summary = summarize_news(text)
    keywords = get_keywords(text)

    conn = sqlite3.connect('static/database.db')
    cursor = conn.cursor()
    command = ("INSERT INTO Chatlog(username, date, question, bias_class, bias_percentage, summary, reason, keywords) "
               "Values(?,?,?,?,?,?,?,?)")
    current_date = now_kst().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(command, (session["username"], current_date, text, bias_class, str(bias_score), summary, reason, keywords))
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

@app.route('/get_response', methods=["POST"])
def get_chatbot_response():
    data = request.json
    text = data["message"]

    bias_class, bias_score, score_lst = get_bias_classification(text)
    reason = reason_news(text, bias_class)
    summary = summarize_news(text)
    keywords = get_keywords(text)

    conn = sqlite3.connect('static/database.db')
    cursor = conn.cursor()
    command = ("INSERT INTO Chatlog(username, date, question, bias_class, bias_percentage, summary, reason, keywords) "
               "Values(?,?,?,?,?,?,?,?)")
    current_date = now_kst().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute(command, (session["username"], current_date, text, bias_class, bias_score, summary, reason, keywords))
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

if __name__ == "__main__":
    app.run(debug=True, port=8080)
