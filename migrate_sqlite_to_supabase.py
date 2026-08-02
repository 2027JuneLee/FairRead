import os
import sqlite3
from typing import Iterable, List, Dict, Any

from supabase import create_client


SQLITE_PATH = os.getenv("SQLITE_PATH", "static/database.db")
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()


def chunked(rows: List[Dict[str, Any]], size: int = 500) -> Iterable[List[Dict[str, Any]]]:
    for i in range(0, len(rows), size):
        yield rows[i:i + size]


def bool_from_sqlite(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def require_env() -> None:
    if not SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL is missing.")
    if not SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY is missing.")
    if "/rest/v1" in SUPABASE_URL:
        raise RuntimeError("SUPABASE_URL should be like https://<project-ref>.supabase.co (no /rest/v1).")
    if SUPABASE_SERVICE_ROLE_KEY.startswith("sb_publishable_"):
        raise RuntimeError("You set a publishable key. Use SUPABASE_SERVICE_ROLE_KEY (server key), not publishable.")


def sqlite_rows(conn: sqlite3.Connection, sql: str) -> List[sqlite3.Row]:
    cur = conn.cursor()
    cur.execute(sql)
    return cur.fetchall()


def upsert_rows(sb, table: str, rows: List[Dict[str, Any]], on_conflict: str) -> None:
    if not rows:
        print(f"{table}: 0 rows")
        return
    total = 0
    for batch in chunked(rows):
        sb.table(table).upsert(batch, on_conflict=on_conflict).execute()
        total += len(batch)
    print(f"{table}: {total} rows")


def main() -> None:
    require_env()
    sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row

    users_src = sqlite_rows(conn, "SELECT username, password, email, gender, age, country, race, religion, politics, recent_login FROM Users")
    users = []
    for r in users_src:
        users.append({
            "username": r["username"],
            "password": r["password"],
            "email": r["email"],
            "gender": r["gender"],
            "age": r["age"],
            "country": r["country"],
            "race": r["race"],
            "religion": r["religion"],
            "politics": r["politics"],
            "recent_login": r["recent_login"],
        })
    upsert_rows(sb, "users", users, "username")

    debates_src = sqlite_rows(conn, "SELECT id, topic, date, isClosed FROM debates")
    debates = []
    for r in debates_src:
        debates.append({
            "id": r["id"],
            "topic": r["topic"],
            "created_at": r["date"],
            "is_closed": bool_from_sqlite(r["isClosed"]),
        })
    upsert_rows(sb, "debates", debates, "id")

    news_src = sqlite_rows(conn, "SELECT id, debate_id, title, link, summary, classification, left, center, right FROM news")
    news = []
    for r in news_src:
        news.append({
            "id": r["id"],
            "debate_id": r["debate_id"],
            "title": r["title"],
            "link": r["link"],
            "summary": r["summary"],
            "classification": r["classification"],
            "left_score": r["left"],
            "center_score": r["center"],
            "right_score": r["right"],
        })
    upsert_rows(sb, "news", news, "id")

    posts_src = sqlite_rows(conn, "SELECT id, debate_id, username, content, timestamp FROM posts")
    posts = []
    for r in posts_src:
        posts.append({
            "id": r["id"],
            "debate_id": r["debate_id"],
            "username": r["username"],
            "content": r["content"],
            "created_at": r["timestamp"],
        })
    upsert_rows(sb, "posts", posts, "id")

    likes_src = sqlite_rows(conn, "SELECT id, post_id, username, timestamp FROM post_likes")
    post_likes = []
    for r in likes_src:
        post_likes.append({
            "id": r["id"],
            "post_id": r["post_id"],
            "username": r["username"],
            "created_at": r["timestamp"],
        })
    upsert_rows(sb, "post_likes", post_likes, "id")

    comments_src = sqlite_rows(conn, "SELECT id, post_id, username, comment, timestamp FROM post_comments")
    post_comments = []
    for r in comments_src:
        post_comments.append({
            "id": r["id"],
            "post_id": r["post_id"],
            "username": r["username"],
            "comment": r["comment"],
            "created_at": r["timestamp"],
        })
    upsert_rows(sb, "post_comments", post_comments, "id")

    votes_src = sqlite_rows(conn, "SELECT id, username, news_id, voted_at FROM news_votes")
    news_votes = []
    for r in votes_src:
        news_votes.append({
            "id": r["id"],
            "username": r["username"],
            "news_id": r["news_id"],
            "voted_at": r["voted_at"],
        })
    upsert_rows(sb, "news_votes", news_votes, "id")

    chatlog_src = sqlite_rows(conn, "SELECT rowid AS id, username, date, question, bias_class, bias_percentage, summary, reason, keywords, COALESCE(is_url, 0) AS is_url FROM Chatlog")
    chatlog = []
    for r in chatlog_src:
        chatlog.append({
            "id": r["id"],
            "username": r["username"],
            "created_at": r["date"],
            "question": r["question"],
            "bias_class": r["bias_class"],
            "bias_percentage": r["bias_percentage"],
            "summary": r["summary"],
            "reason": r["reason"],
            "keywords": r["keywords"],
            "is_url": bool_from_sqlite(r["is_url"]),
        })
    upsert_rows(sb, "chatlog", chatlog, "id")

    ann_src = sqlite_rows(conn, """
        SELECT id, article_id, user_id, target_language, term, term_type, definition,
               english_meaning, example_sentence, difficulty, part_of_speech, grammar_note,
               article_language, created_at
        FROM learning_annotations
    """)
    learning_annotations = []
    for r in ann_src:
        learning_annotations.append({
            "id": r["id"],
            "article_id": r["article_id"],
            "user_id": r["user_id"],
            "target_language": r["target_language"],
            "term": r["term"],
            "term_type": r["term_type"],
            "definition": r["definition"],
            "english_meaning": r["english_meaning"],
            "example_sentence": r["example_sentence"],
            "difficulty": r["difficulty"],
            "part_of_speech": r["part_of_speech"],
            "grammar_note": r["grammar_note"],
            "article_language": r["article_language"],
            "created_at": r["created_at"],
        })
    upsert_rows(sb, "learning_annotations", learning_annotations, "id")

    conn.close()
    print("Migration complete.")


if __name__ == "__main__":
    main()
