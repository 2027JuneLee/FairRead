import os
import shutil
import sqlite3
import random
from datetime import datetime, timedelta
import string

DB_PATH = "static/database.db"

# ------------- helpers -------------
def backup_db(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"DB not found at {path}. Launch the app once to create it, or adjust DB_PATH.")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{path}.bak_{ts}"
    shutil.copy2(path, backup)
    print(f"Backup created -> {backup}")

def rand_sentence(min_words=6, max_words=14):
    words = [
        "election","policy","global","economy","health","science","technology","education",
        "research","market","privacy","security","community","climate","energy","innovation",
        "sports","culture","media","platform","campaign","court","governance","trade","finance",
        "housing","transport","labor","rights","regulation"
    ]
    n = random.randint(min_words, max_words)
    return " ".join(random.choice(words) for _ in range(n)).capitalize() + "."

def draw_bias_triplet():
    # Create a random L/C/R triplet summing to 100
    a, b = random.randint(0, 100), random.randint(0, 100)
    arr = sorted([a, b, 0, 100])
    L = arr[1] - arr[0]
    C = arr[2] - arr[1]
    R = arr[3] - arr[2]
    # slight smoothing
    tweak = random.choice([-2,-1,0,1,2])
    L = max(0, min(100, L+tweak))
    R = max(0, min(100, R-tweak))
    C = max(0, 100 - L - R)
    return [L, C, R]

def classify_from_triplet(triplet):
    idx = max(range(3), key=lambda i: triplet[i])
    return ["left", "center", "right"][idx]

# ------------- main seeding -------------
def seed():
    backup_db(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Ensure columns we rely on exist (best effort, non-destructive)
    # (If your schema already has these, these ALTERs will be skipped.)
    try:
        cur.execute("ALTER TABLE Users ADD COLUMN recent_login TEXT;")
    except Exception:
        pass

    # --- Users ---
    first_names = ["Alex","Jordan","Taylor","Sam","Morgan","Chris","Jamie","Riley","Casey","Avery",
                   "Drew","Quinn","Cameron","Rowan","Reese","Harper","Logan","Peyton","Skyler","Evan"]
    last_names  = ["Lee","Kim","Patel","Garcia","Smith","Brown","Davis","Martin","Lopez","Clark",
                   "Young","King","Wright","Scott","Green","Baker","Adams","Nelson","Hill","Carter"]
    genders = ["Male","Female","Other"]
    politics = ["left","center","right","libertarian","green","independent"]
    countries = ["US","CA","UK","DE","SE","KR","IN","SG","AU","NZ"]
    races = ["Asian","Black","White","Hispanic","Mixed","Other"]
    religions = ["None","Christian","Muslim","Jewish","Hindu","Buddhist","Other"]

    user_count_target = 75
    print(f"Seeding ~{user_count_target} users...")

    for i in range(user_count_target):
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        username = f"{fn.lower()}{ln.lower()}{random.randint(1,999)}"
        email = f"{username}@example.com"
        gender = random.choice(genders)
        age = random.randint(18, 70)
        pol = random.choice(politics)
        country = random.choice(countries)
        race = random.choice(races)
        religion = random.choice(religions)
        # Spread recent_login across last 45 days (some will be inactive >30d)
        recent_login_dt = datetime.now() - timedelta(days=random.randint(0, 45),
                                                     hours=random.randint(0,23),
                                                     minutes=random.randint(0,59))
        recent_login = recent_login_dt.strftime('%Y-%m-%d %H:%M:%S')

        cur.execute("""
            INSERT OR IGNORE INTO Users (username, password, email, gender, age, country, race, religion, politics, recent_login)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (username, "password123", email, gender, age, country, race, religion, pol, recent_login))

    conn.commit()

    # Fetch the actual usernames in DB (including pre-existing)
    cur.execute("SELECT username FROM Users;")
    all_users = [r[0] for r in cur.fetchall()]
    if not all_users:
        raise RuntimeError("No users present after seeding attempt. Check your Users table schema.")

    # --- Chatlog ---
    print("Seeding Chatlog entries (6 months back)...")
    keywords_pool = [
        "AI", "Elections", "Policy", "Economy", "Healthcare", "Education", "Climate Change",
        "Energy", "Privacy", "Security", "Immigration", "Supreme Court", "Tech Regulation",
        "Social Media", "Foreign Policy", "Sports", "Culture", "Housing", "Labor", "Transportation"
    ]

    # Spread entries over last ~180 days
    start_date = datetime.now() - timedelta(days=180)
    total_entries_target = 3000  # rich data
    for _ in range(total_entries_target):
        user = random.choice(all_users)
        # random date in last 6 months
        d = start_date + timedelta(days=random.randint(0, 180),
                                   hours=random.randint(0, 23),
                                   minutes=random.randint(0, 59),
                                   seconds=random.randint(0, 59))
        date_str = d.strftime('%Y-%m-%d %H:%M:%S')

        q = rand_sentence(8, 18)
        triplet = draw_bias_triplet()
        bias_class = classify_from_triplet(triplet)
        bias_percentage = str(triplet)  # store as stringified list: "[L, C, R]"

        # Pick 1-3 keywords (store as list or comma string—your stats code handles both)
        kw_count = random.choice([1,1,2,2,2,3])
        kws = random.sample(keywords_pool, k=kw_count)
        keywords_val = str(kws)  # e.g., "['AI', 'Economy']"

        summary = rand_sentence(12, 20)
        reason = f"Detected {bias_class} leaning due to language cues and source references."

        cur.execute("""
            INSERT INTO Chatlog (username, date, question, bias_class, bias_percentage, summary, reason, keywords)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (user, date_str, q, bias_class, bias_percentage, summary, reason, keywords_val))

        # Optional: batch commit for speed
        if _ % 500 == 0:
            conn.commit()

    conn.commit()
    conn.close()
    print("✅ Mock data seeding complete!")

if __name__ == "__main__":
    seed()
