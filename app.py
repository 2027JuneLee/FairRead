import ast
import json
import os
import sys
import time

from collections import Counter, defaultdict
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, abort
from datetime import datetime, timedelta, date
from werkzeug.utils import secure_filename
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

app = Flask(__name__)

app.config['APP_TZ'] = ZoneInfo("Asia/Seoul")

app.secret_key = "abc"

# Ensure Vercel finds local modules in the same directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

from chatbot import *
from helper import *
load_dotenv()

url: str = (os.getenv("SUPABASE_URL") or "").strip()
key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")

supabase: Client = None

url = url.rstrip("/")
if url.lower().endswith("/rest/v1"):
    url = url[:-8].rstrip("/")

if url and key:
    supabase = create_client(url, key)
else:
    print("WARNING: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_KEY) is missing.")


def _extract_missing_column_name(error: APIError):
    payload = error.args[0] if error.args else None
    message = payload.get("message", "") if isinstance(payload, dict) else str(error)
    marker = "Could not find the '"
    if marker not in message:
        return None
    start = message.find(marker) + len(marker)
    end = message.find("' column", start)
    if end <= start:
        return None
    return message[start:end]


def _supabase_insert_resilient(table_name, payload):
    working = dict(payload)
    while True:
        try:
            return supabase.table(table_name).insert(working).execute()
        except APIError as e:
            missing_col = _extract_missing_column_name(e)
            if missing_col and missing_col in working:
                working.pop(missing_col, None)
                continue
            raise


def _api_error_payload(error: APIError):
    payload = error.args[0] if error.args else None
    return payload if isinstance(payload, dict) else {}


def _api_error_message(error: APIError):
    payload = _api_error_payload(error)
    return payload.get("message", "") or str(error)


def _api_error_code(error: APIError):
    payload = _api_error_payload(error)
    return payload.get("code")


def _next_numeric_id(table_name):
    latest_res = (
        supabase.table(table_name)
        .select("id")
        .order("id", desc=True)
        .limit(1)
        .execute()
    )
    latest = (latest_res.data or [None])[0]
    latest_id = _pick_row_value(latest, "id", default=0) if latest else 0
    try:
        return int(latest_id) + 1
    except (TypeError, ValueError):
        raise RuntimeError(f"{table_name}.id is not numeric: {latest_id!r}")


def _insert_chatlog_resilient(payload):
    working = dict(payload)
    if "id" not in working or working.get("id") is None:
        working["id"] = _next_numeric_id("chatlog")
    id_retry_count = 0
    while True:
        try:
            return supabase.table("chatlog").insert(working).execute()
        except APIError as e:
            missing_col = _extract_missing_column_name(e)
            if missing_col and missing_col in working:
                working.pop(missing_col, None)
                continue

            message = _api_error_message(e)
            code = _api_error_code(e)
            needs_manual_id = (
                code == "23502"
                and 'column "id"' in message
                and "chatlog" in message
            )
            duplicate_id = code == "23505" and "id" in working
            if (needs_manual_id or duplicate_id) and id_retry_count < 3:
                working["id"] = _next_numeric_id("chatlog")
                id_retry_count += 1
                continue
            raise


def _pick_row_value(row, *keys, default=None):
    for key in keys:
        value = row.get(key) if isinstance(row, dict) else None
        if value is not None:
            return value
    return default


def _coerce_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def _display_date(value):
    if value is None:
        return ""
    text = str(value)
    if "T" in text:
        return text.replace("T", " ")[:19]
    return text

def now_kst():

    return datetime.now(app.config['APP_TZ'])



def current_user():

    return session.get("username")



def is_admin_user():

    return current_user() == "testtest"



# Translation dictionaries

BIAS_LABELS = {

    'en': {'Left': 'Left', 'Center': 'Center', 'Right': 'Right'},

    'es': {'Left': 'Izquierda', 'Center': 'Centro', 'Right': 'Derecha'},

    'zh': {'Left': '左翼', 'Center': '中立', 'Right': '右翼'},

    'ko': {'Left': '좌파', 'Center': '중도', 'Right': '우파'}

}



UI_LABELS = {
    "en": {
        "Home": "Home",
        "News": "News",
        "Learn": "Learn",
        "Debate": "Debate",
        "Profile": "Profile",
        "Statistics": "Statistics",
        "Login": "Login",
        "Logout": "Logout",
        "Bias Classification": "Bias Classification",
        "Summary": "Summary",
        "Keywords": "Keywords",
        "Reason": "Reason",
        "Username": "Username",
        "Password": "Password",
        "Not a member?": "Not a member?",
        "Sign up": "Sign up",
        "Select your gender": "Select your gender",
        "Select your birthday": "Select your birthday",
        "Male": "Male",
        "Female": "Female",
        "Other": "Other",
        "Register": "Register",
        "Registration complete": "Registration complete",
        "Your account was created successfully. You can now sign in.": "Your account was created successfully. You can now sign in.",
        "Go to Login": "Go to Login",
        "Already have an account?": "Already have an account?",
        "Sign in": "Sign in",
        "News Classifier": "News Classifier",
        "We will classify the news for you!": "We will classify the news for you!",
        "How to use": "How to use",
        "Attach File": "Attach File",
        "Paste or type article text or notes here...": "Paste or type article text or notes here...",
        "Class": "Class",
        "Bias Class": "Bias Class",
        "Bias Class:": "Bias Class:",
        "Bias Scores": "Bias Scores",
        "Bias Scores:": "Bias Scores:",
        "Left": "Left",
        "Center": "Center",
        "Right": "Right",
        "Left:": "Left:",
        "Center:": "Center:",
        "Right:": "Right:",
        "Not analyzed yet": "Not analyzed yet",
        "Reason for Bias": "Reason for Bias",
        "Analysis pending...": "Analysis pending...",
        "News Summary": "News Summary",
        "Summary will appear here...": "Summary will appear here...",
        "Keywords will be shown here...": "Keywords will be shown here...",
        "How to use the News Classifier": "How to use the News Classifier",
        "Ways to submit": "Ways to submit",
        "Paste text": "Paste text",
        "Paste any article text or your notes, then press Enter or click the send icon.": "Paste any article text or your notes, then press Enter or click the send icon.",
        "Paste a link": "Paste a link",
        "Drop an article URL. We'll fetch its content when possible and analyze it.": "Drop an article URL. We'll fetch its content when possible and analyze it.",
        "Upload a file": "Upload a file",
        "PDF or DOCX supported. If a file is attached, it takes priority over typed text.": "PDF or DOCX supported. If a file is attached, it takes priority over typed text.",
        "Hello! You can copy and paste the news text or link, or upload a PDF file. The analysis results will appear on the right.": "Hello! You can copy and paste the news text or link, or upload a PDF file. The analysis results will appear on the right.",
        "What you'll see": "What you'll see",
        "Left / Center / Right Scores": "Left / Center / Right Scores",
        "Tips & limits": "Tips & limits",
        "Filenames should be English letters/numbers only": "Filenames should be English letters/numbers only",
        "For paywalled pages, paste the article text or upload a PDF.": "For paywalled pages, paste the article text or upload a PDF.",
        "Very long documents can take longer to process.": "Very long documents can take longer to process.",
        "If content extraction fails, try another link or paste the text directly.": "If content extraction fails, try another link or paste the text directly.",
        "We analyze your input and show results on the right.": "We analyze your input and show results on the right.",
        "Got it": "Got it",
        "Analyzing, please wait...": "Analyzing, please wait...",
        "Error fetching URL": "Error fetching URL",
        "Unable to fetch article (HTTP error). Website may be blocking automated access.": "Unable to fetch article (HTTP error). Website may be blocking automated access.",
        "This article appears to be behind a paywall. Please try copying the text directly or accessing via an archive service.": "This article appears to be behind a paywall. Please try copying the text directly or accessing via an archive service.",
        "Request timed out. The website is taking too long to respond.": "Request timed out. The website is taking too long to respond.",
        "Connection error. Please check the URL and your internet connection.": "Connection error. Please check the URL and your internet connection.",
        "Unable to extract article content. The website structure may not be supported.": "Unable to extract article content. The website structure may not be supported.",
        "Article text is too short or could not be extracted.": "Article text is too short or could not be extracted.",
        "Please rename the file using only English letters, numbers, spaces, underscores, hyphens, and dots (e.g., news_article_2025.pdf).": "Please rename the file using only English letters, numbers, spaces, underscores, hyphens, and dots (e.g., news_article_2025.pdf).",
        "Done Processing. Please check the right side.": "Done Processing. Please check the right side.",
        "Please attach a file or enter a message.": "Please attach a file or enter a message.",
        "Filename not allowed. Use only English letters, numbers, spaces, underscores, hyphens, and dots.": "Filename not allowed. Use only English letters, numbers, spaces, underscores, hyphens, and dots.",
        "My Data": "My Data",
        "No data yet": "No data yet",
        "Classify your first article to see bias distribution and topics here.": "Classify your first article to see bias distribution and topics here.",
        "Start classifying": "Start classifying",
        "Bias Distribution": "Bias Distribution",
        "Average across your submissions": "Average across your submissions",
        "Top Topics": "Top Topics",
        "Most frequent keywords": "Most frequent keywords",
        "Recent Classifications": "Recent Classifications",
        "Prev": "Prev",
        "Next": "Next",
        "No recent items": "No recent items",
        "Your latest classifications will appear here after you analyze an article.": "Your latest classifications will appear here after you analyze an article.",
        "Analyze an article": "Analyze an article",
        "Class:": "Class:",
        "Mentions": "Mentions",
        "Total Users": "Total Users",
        "Active Users (30d)": "Active Users (30d)",
        "Total News": "Total News",
        "Recent News (30d)": "Recent News (30d)",
        "Chatbot Usage (Last 7 Days)": "Chatbot Usage (Last 7 Days)",
        "Daily requests": "Daily requests",
        "Monthly Chatbot Usage": "Monthly Chatbot Usage",
        "By month": "By month",
        "User Growth": "User Growth",
        "Accounts over time": "Accounts over time",
        "Top Keywords": "Top Keywords",
        "Most frequent": "Most frequent",
        "Daily User Sessions": "Daily User Sessions",
        "Last 7 days": "Last 7 days",
        "Average Bias Scores": "Average Bias Scores",
        "All": "All",
        "Chatbot Usage": "Chatbot Usage",
        "Sessions": "Sessions",
        "Users": "Users",
        "Created on": "Created on",
        "Back to Debates": "Back to Debates",
        "Create Post": "Create Post",
        "Add Related News": "Add Related News",
        "Discussion": "Discussion",
        "Delete": "Delete",
        "Like": "Like",
        "Comments": "Comments",
        "Write a comment…": "Write a comment…",
        "No posts yet. Be the first to contribute to the discussion.": "No posts yet. Be the first to contribute to the discussion.",
        "Related News": "Related News",
        "More": "More",
        "Open original article": "Open original article",
        "Bias & Scores": "Bias & Scores",
        "Classification:": "Classification:",
        "Cast your view on this article's bias to see the full breakdown.": "Cast your view on this article's bias to see the full breakdown.",
        "Read Full Article": "Read Full Article",
        "Close": "Close",
        "What is your opinion about this article's bias?": "What is your opinion about this article's bias?",
        "No news articles have been added yet.": "No news articles have been added yet.",
        "Delete this post? This cannot be undone.": "Delete this post? This cannot be undone.",
        "Delete this news item? This cannot be undone.": "Delete this news item? This cannot be undone.",
        "Debates": "Debates",
        "Open": "Open",
        "Open:": "Open:",
        "Closed": "Closed",
        "Closed:": "Closed:",
        "e.g., Should social media platforms be regulated like utilities?": "e.g., Should social media platforms be regulated like utilities?",
        "Create Debate": "Create Debate",
        "Filter topics...": "Filter topics...",
        "Newest": "Newest",
        "Oldest": "Oldest",
        "A → Z": "A → Z",
        "Z → A": "Z → A",
        "Created:": "Created:",
        "View": "View",
        "Close Debate": "Close Debate",
        "No open debates yet.": "No open debates yet.",
        "No closed debates yet.": "No closed debates yet.",
        "Debate Topic": "Debate Topic",
        "Share Your Thoughts": "Share Your Thoughts",
        "Your Post": "Your Post",
        "Write a clear, constructive contribution to the debate…": "Write a clear, constructive contribution to the debate…",
        "Suggested length:": "Suggested length:",
        "50–500 words": "50–500 words",
        "/2000": "/2000",
        "Please revise your post to remove disallowed terms and ensure it's on-topic.": "Please revise your post to remove disallowed terms and ensure it's on-topic.",
        "Back to Debate": "Back to Debate",
        "Submit Post": "Submit Post",
        "Please add a bit more detail (at least ~10 words).": "Please add a bit more detail (at least ~10 words).",
        "Please keep your post on-topic and respectful. Posts are visible to others.": "Please keep your post on-topic and respectful. Posts are visible to others.",
        "Stay relevant to": "Stay relevant to",
        "Support claims with sources when possible.": "Support claims with sources when possible.",
        "Use civil language. Critique ideas, not people.": "Use civil language. Critique ideas, not people.",
        "No hate speech, harassment, or calls for violence. Avoid slurs and personal data.": "No hate speech, harassment, or calls for violence. Avoid slurs and personal data.",
        "No unrelated spam or promotional content.": "No unrelated spam or promotional content.",
        "Add News Article": "Add News Article",
        "Attach a credible source, summarize clearly, and keep it civil.": "Attach a credible source, summarize clearly, and keep it civil.",
        "We store title, link, summary & content to compute bias scores.": "We store title, link, summary & content to compute bias scores.",
        "Article Title": "Article Title",
        "Enter the article headline…": "Enter the article headline…",
        "Keep it faithful to the original headline.": "Keep it faithful to the original headline.",
        "Article Link": "Article Link",
        "https://example.com/news/article": "https://example.com/news/article",
        "We'll try to pull the full text from the URL for you to review and edit.": "We'll try to pull the full text from the URL for you to review and edit.",
        "Extract Content": "Extract Content",
        "Summarize the article in 2–3 sentences…": "Summarize the article in 2–3 sentences…",
        "Be neutral and concise; avoid personal opinions here.": "Be neutral and concise; avoid personal opinions here.",
        "News Content": "News Content",
        "Paste or edit the extracted article text…": "Paste or edit the extracted article text…",
        "Edit for clarity. Don't include unrelated or harmful content.": "Edit for clarity. Don't include unrelated or harmful content.",
        "Guidelines": "Guidelines",
        "Stay on topic and cite credible sources.": "Stay on topic and cite credible sources.",
        "No hate speech, harassment, or personal attacks.": "No hate speech, harassment, or personal attacks.",
        "Report misclassified or suspicious sources to an admin.": "Report misclassified or suspicious sources to an admin.",
        "After submission, bias and stance will be computed automatically.": "After submission, bias and stance will be computed automatically.",
        "Submit News": "Submit News",
        "Please paste a valid link first.": "Please paste a valid link first.",
        "Extracting…": "Extracting…",
        "Error:": "Error:",
        "Failed to extract content.": "Failed to extract content.",
        "Request failed. Please check the link or try again later.": "Request failed. Please check the link or try again later.",
        "Bias • Summary • Transparency": "Bias • Summary • Transparency",
        "See the story behind the story.": "See the story behind the story.",
        "FairRead analyzes any article for political lean, explains why, and returns a concise summary you can trust.": "FairRead analyzes any article for political lean, explains why, and returns a concise summary you can trust.",
        "Analyze an Article": "Analyze an Article",
        "Explore Features": "Explore Features",
        "Private by default • URL · Text · PDF": "Private by default • URL · Text · PDF",
        "Preview": "Preview",
        "Bias · Confidence · Key signals": "Bias · Confidence · Key signals",
        "About": "About",
        "FairRead explained": "FairRead explained",
        "FairRead is a lightweight tool for evaluating news articles with clarity and speed. Paste a link, text, or PDF and receive an objective read on where the piece leans.": "FairRead is a lightweight tool for evaluating news articles with clarity and speed. Paste a link, text, or PDF and receive an objective read on where the piece leans.",
        "Results include a brief rationale so you can see the cues behind the call — not just the label. Your history stays private and helps you understand your own reading patterns over time.": "Results include a brief rationale so you can see the cues behind the call — not just the label. Your history stays private and helps you understand your own reading patterns over time.",
        "Bias classification with confidence": "Bias classification with confidence",
        "Evidence-based rationale (framing, sources, wording)": "Evidence-based rationale (framing, sources, wording)",
        "Concise, source-aware summary": "Concise, source-aware summary",
        "Personal analytics with privacy by default": "Personal analytics with privacy by default",
        "Capabilities": "Capabilities",
        "A focused toolkit for reading news clearly": "A focused toolkit for reading news clearly",
        "Everything you need to judge an article—nothing you don't.": "Everything you need to judge an article—nothing you don't.",
        "Bias classification with rationale": "Bias classification with rationale",
        "Left / center / right paired with the specific cues that informed the call (framing, sources, wording).": "Left / center / right paired with the specific cues that informed the call (framing, sources, wording).",
        "Clear, skimmable summaries that preserve context and map claims to evidence.": "Clear, skimmable summaries that preserve context and map claims to evidence.",
        "Learning features": "Learning features",
        "Study article terms": "Study article terms",
        "Open the Learn tab after analysis to review vocabulary, idioms, and grammar in the article language with English support.": "Open the Learn tab after analysis to review vocabulary, idioms, and grammar in the article language with English support.",
        "Learning mode": "Learning mode",
        "Practice terms from your articles and keep them in the article language.": "Practice terms from your articles and keep them in the article language.",
        "Private reading analytics": "Private reading analytics",
        "See trends in outlets and perspectives over time—stored locally by default.": "See trends in outlets and perspectives over time—stored locally by default.",
        "Flexible inputs": "Flexible inputs",
        "Analyze URLs, pasted text, or PDFs. Robust parsing for long-form pieces.": "Analyze URLs, pasted text, or PDFs. Robust parsing for long-form pieces.",
        "Quality & controls": "Quality & controls",
        "Deterministic modes for consistency and clear versioned outputs for sharing.": "Deterministic modes for consistency and clear versioned outputs for sharing.",
        "Getting Started": "Getting Started",
        "How to Use FairRead": "How to Use FairRead",
        "Follow three quick steps to analyze any news article with clarity and transparency.": "Follow three quick steps to analyze any news article with clarity and transparency.",
        "1. Provide the article": "1. Provide the article",
        "Enter a link, paste the text, or upload a PDF.": "Enter a link, paste the text, or upload a PDF.",
        "2. Let AI analyze": "2. Let AI analyze",
        "FairRead detects political bias, highlights key signals, and summarizes the piece.": "FairRead detects political bias, highlights key signals, and summarizes the piece.",
        "3. Review insights": "3. Review insights",
        "See the bias label, rationale, and a concise summary you can trust.": "See the bias label, rationale, and a concise summary you can trust.",
        "Community": "Community",
        "Discuss, compare, and learn together": "Discuss, compare, and learn together",
        "Join focused debate rooms on live topics, compare evidence, and see how perspectives shift—without sacrificing civility or privacy.": "Join focused debate rooms on live topics, compare evidence, and see how perspectives shift—without sacrificing civility or privacy.",
        "Explore Debate Rooms": "Explore Debate Rooms",
        "Topic-Focused Rooms": "Topic-Focused Rooms",
        "Join curated rooms on specific policy issues. Keep discussions on track with structured prompts and timeboxed rounds.": "Join curated rooms on specific policy issues. Keep discussions on track with structured prompts and timeboxed rounds.",
        "Weekly prompts and summaries": "Weekly prompts and summaries",
        "Invite-only or public access": "Invite-only or public access",
        "Evidence-Linked Posts": "Evidence-Linked Posts",
        "Back claims with links or PDFs. FairRead highlights bias signals in cited content so participants can assess sources quickly.": "Back claims with links or PDFs. FairRead highlights bias signals in cited content so participants can assess sources quickly.",
        "Inline article analysis": "Inline article analysis",
        "Quote and counter-quote threads": "Quote and counter-quote threads",
        "Civility & Privacy": "Civility & Privacy",
        "Moderation tools and private rooms reduce noise. Participation history stays local by default; share only what you choose.": "Moderation tools and private rooms reduce noise. Participation history stays local by default; share only what you choose.",
        "Report & mute controls": "Report & mute controls",
        "Privacy-first analytics": "Privacy-first analytics",
        "Weekly Topic": "Weekly Topic",
        "Each week introduces a new debate prompt with a short neutral brief to frame the discussion.": "Each week introduces a new debate prompt with a short neutral brief to frame the discussion.",
        "Structured Rounds": "Structured Rounds",
        "Opening statements, evidence posts, and closing remarks keep conversations concise and comparable.": "Opening statements, evidence posts, and closing remarks keep conversations concise and comparable.",
        "Outcome Snapshot": "Outcome Snapshot",
        "See a neutral wrap-up: main claims, strongest evidence cited, and perspective shift over the week.": "See a neutral wrap-up: main claims, strongest evidence cited, and perspective shift over the week.",
        "© 2024~2026 FairRead. All Rights Reserved.": "© 2024~2026 FairRead. All Rights Reserved.",
        "Learn from this article": "Learn from this article",
        "Learning Term Review": "Learning Term Review",
        "Review extracted terms by timeframe.": "Review extracted terms by timeframe.",
        "Day": "Day",
        "Week": "Week",
        "Month": "Month",
        "No learning terms yet": "No learning terms yet",
        "Terms from your learned articles will appear here.": "Terms from your learned articles will appear here.",
        "Week of": "Week of",
        "All Terms": "All Terms",
        "Learned": "Learned",
        "Not learned": "Not learned",
        "Learning Terms": "Learning Terms",
        "Click any term to see details": "Click any term to see details",
        "Vocabulary": "Vocabulary",
        "Idiom": "Idiom",
        "Grammar": "Grammar pattern",
        "Beginner": "Beginner",
        "Intermediate": "Intermediate",
        "Advanced": "Advanced",
        "Definition": "Definition",
        "Example": "Example",
        "Part of Speech": "Part of Speech",
        "Difficulty": "Difficulty",
        "Grammar Note": "Grammar Note",
        "Your language": "Your language",
        "Article language": "Article language",
        "Total Terms": "Total Terms",
        "Back to Analysis": "Back to Analysis",
        "Generating learning terms...": "Generating learning terms...",
        "Extracting learning terms...": "Extracting learning terms...",
        "This usually takes 10-30 seconds.": "This usually takes 10-30 seconds.",
        "Still working...": "Still working...",
        "If this takes too long, please refresh.": "If this takes too long, please refresh.",
        "Extraction is taking longer than expected.": "Extraction is taking longer than expected.",
        "Failed to generate learning terms.": "Failed to generate learning terms.",
    },
    "es": {
        "Home": "Inicio",
        "News": "Noticias",
        "Learn": "Aprender",
        "Debate": "Debate",
        "Profile": "Perfil",
        "Statistics": "Estadísticas",
        "Login": "Iniciar sesión",
        "Logout": "Cerrar sesión",
        "Bias Classification": "Clasificación de sesgo",
        "Summary": "Resumen",
        "Keywords": "Palabras clave",
        "Reason": "Razón",
        "Username": "Nombre de usuario",
        "Password": "Contraseña",
        "Not a member?": "¿No tienes cuenta?",
        "Sign up": "Regístrate",
        "Select your gender": "Selecciona tu género",
        "Select your birthday": "Selecciona tu fecha de nacimiento",
        "Male": "Masculino",
        "Female": "Femenino",
        "Other": "Otro",
        "Register": "Registrarse",
        "Registration complete": "Registro completado",
        "Your account was created successfully. You can now sign in.": "Tu cuenta se creó correctamente. Ahora puedes iniciar sesión.",
        "Go to Login": "Ir al inicio de sesión",
        "Already have an account?": "¿Ya tienes una cuenta?",
        "Sign in": "Iniciar sesión",
        "News Classifier": "Clasificador de noticias",
        "We will classify the news for you!": "¡Clasificaremos la noticia por ti!",
        "How to use": "Cómo usarlo",
        "Attach File": "Adjuntar archivo",
        "Paste or type article text or notes here...": "Pega o escribe aquí el texto del artículo o tus notas...",
        "Class": "Clase",
        "Bias Class": "Clase de sesgo",
        "Bias Class:": "Clase de sesgo:",
        "Bias Scores": "Puntuaciones de sesgo",
        "Bias Scores:": "Puntuaciones de sesgo:",
        "Left": "Izquierda",
        "Center": "Centro",
        "Right": "Derecha",
        "Left:": "Izquierda:",
        "Center:": "Centro:",
        "Right:": "Derecha:",
        "Not analyzed yet": "Aún no analizado",
        "Reason for Bias": "Motivo del sesgo",
        "Analysis pending...": "Análisis pendiente...",
        "News Summary": "Resumen de la noticia",
        "Summary will appear here...": "El resumen aparecerá aquí...",
        "Keywords will be shown here...": "Las palabras clave se mostrarán aquí...",
        "How to use the News Classifier": "Cómo usar el clasificador de noticias",
        "Ways to submit": "Formas de envío",
        "Paste text": "Pegar texto",
        "Paste any article text or your notes, then press Enter or click the send icon.": "Pega el texto de cualquier artículo o tus notas y luego presiona Enter o haz clic en el icono de enviar.",
        "Paste a link": "Pegar un enlace",
        "Drop an article URL. We'll fetch its content when possible and analyze it.": "Introduce la URL de un artículo. Recuperaremos su contenido cuando sea posible y lo analizaremos.",
        "Upload a file": "Subir un archivo",
        "PDF or DOCX supported. If a file is attached, it takes priority over typed text.": "Compatible con PDF o DOCX. Si adjuntas un archivo, tendrá prioridad sobre el texto escrito.",
        "What you'll see": "Lo que verás",
        "Left / Center / Right Scores": "Puntuaciones de izquierda / centro / derecha",
        "Tips & limits": "Consejos y límites",
        "Filenames should be English letters/numbers only": "Los nombres de archivo deben usar solo letras y números en inglés",
        "For paywalled pages, paste the article text or upload a PDF.": "En páginas con muro de pago, pega el texto del artículo o sube un PDF.",
        "Very long documents can take longer to process.": "Los documentos muy largos pueden tardar más en procesarse.",
        "If content extraction fails, try another link or paste the text directly.": "Si falla la extracción del contenido, prueba con otro enlace o pega el texto directamente.",
        "We analyze your input and show results on the right.": "Analizamos tu contenido y mostramos los resultados a la derecha.",
        "Got it": "Entendido",
        "Hello! You can copy and paste the news text or link, or upload a PDF file. The analysis results will appear on the right.": "¡Hola! Puedes copiar y pegar el texto de la noticia o un enlace, o subir un archivo PDF. Los resultados del análisis aparecerán a la derecha.",
        "Analyzing, please wait...": "Analizando, por favor espera...",
        "Error fetching URL": "Error al obtener la URL",
        "Unable to fetch article (HTTP error). Website may be blocking automated access.": "No se puede obtener el artículo (error HTTP). El sitio web puede estar bloqueando el acceso automatizado.",
        "This article appears to be behind a paywall. Please try copying the text directly or accessing via an archive service.": "Este artículo parece estar detrás de un muro de pago. Intenta copiar el texto directamente o acceder a través de un servicio de archivo.",
        "Request timed out. The website is taking too long to respond.": "La solicitud ha expirado. El sitio web está tardando demasiado en responder.",
        "Connection error. Please check the URL and your internet connection.": "Error de conexión. Revisa la URL y tu conexión a Internet.",
        "Unable to extract article content. The website structure may not be supported.": "No se puede extraer el contenido del artículo. Es posible que la estructura del sitio web no sea compatible.",
        "Article text is too short or could not be extracted.": "El texto del artículo es demasiado corto o no se pudo extraer.",
        "Please rename the file using only English letters, numbers, spaces, underscores, hyphens, and dots (e.g., news_article_2025.pdf).": "Cambia el nombre del archivo usando solo letras en inglés, números, espacios, guiones bajos, guiones y puntos (p. ej., news_article_2025.pdf).",
        "Done Processing. Please check the right side.": "Procesamiento completado. Revisa el lado derecho.",
        "Please attach a file or enter a message.": "Adjunta un archivo o escribe un mensaje.",
        "Filename not allowed. Use only English letters, numbers, spaces, underscores, hyphens, and dots.": "Nombre de archivo no permitido. Usa solo letras en inglés, números, espacios, guiones bajos, guiones y puntos.",
        "My Data": "Mis datos",
        "No data yet": "Aún no hay datos",
        "Classify your first article to see bias distribution and topics here.": "Clasifica tu primer artículo para ver aquí la distribución de sesgo y los temas.",
        "Start classifying": "Empezar a clasificar",
        "Bias Distribution": "Distribución de sesgo",
        "Average across your submissions": "Promedio de tus envíos",
        "Top Topics": "Temas principales",
        "Most frequent keywords": "Palabras clave más frecuentes",
        "Recent Classifications": "Clasificaciones recientes",
        "Prev": "Anterior",
        "Next": "Siguiente",
        "No recent items": "No hay elementos recientes",
        "Your latest classifications will appear here after you analyze an article.": "Tus clasificaciones más recientes aparecerán aquí después de analizar un artículo.",
        "Analyze an article": "Analizar un artículo",
        "Class:": "Clase:",
        "Mentions": "Menciones",
        "Total Users": "Usuarios totales",
        "Active Users (30d)": "Usuarios activos (30 d)",
        "Total News": "Total de noticias",
        "Recent News (30d)": "Noticias recientes (30 d)",
        "Chatbot Usage (Last 7 Days)": "Uso del chatbot (últimos 7 días)",
        "Daily requests": "Solicitudes diarias",
        "Monthly Chatbot Usage": "Uso mensual del chatbot",
        "By month": "Por mes",
        "User Growth": "Crecimiento de usuarios",
        "Accounts over time": "Cuentas a lo largo del tiempo",
        "Top Keywords": "Palabras clave principales",
        "Most frequent": "Más frecuentes",
        "Daily User Sessions": "Sesiones diarias de usuarios",
        "Last 7 days": "Últimos 7 días",
        "Average Bias Scores": "Puntuaciones promedio de sesgo",
        "All": "Todos",
        "Chatbot Usage": "Uso del chatbot",
        "Sessions": "Sesiones",
        "Users": "Usuarios",
        "Created on": "Creado el",
        "Back to Debates": "Volver a Debates",
        "Create Post": "Crear publicación",
        "Add Related News": "Agregar noticia relacionada",
        "Discussion": "Discusión",
        "Delete": "Eliminar",
        "Like": "Me gusta",
        "Comments": "Comentarios",
        "Write a comment…": "Escribe un comentario…",
        "No posts yet. Be the first to contribute to the discussion.": "Aún no hay publicaciones. Sé la primera persona en contribuir a la discusión.",
        "Related News": "Noticias relacionadas",
        "More": "Más",
        "Open original article": "Abrir artículo original",
        "Bias & Scores": "Sesgo y puntuaciones",
        "Classification:": "Clasificación:",
        "Cast your view on this article's bias to see the full breakdown.": "Comparte tu opinión sobre el sesgo de este artículo para ver el desglose completo.",
        "Read Full Article": "Leer artículo completo",
        "Close": "Cerrar",
        "What is your opinion about this article's bias?": "¿Cuál es tu opinión sobre el sesgo de este artículo?",
        "No news articles have been added yet.": "Aún no se han agregado artículos de noticias.",
        "Delete this post? This cannot be undone.": "¿Eliminar esta publicación? Esta acción no se puede deshacer.",
        "Delete this news item? This cannot be undone.": "¿Eliminar esta noticia? Esta acción no se puede deshacer.",
        "Debates": "Debates",
        "Open": "Abiertos",
        "Open:": "Abiertos:",
        "Closed": "Cerrados",
        "Closed:": "Cerrados:",
        "e.g., Should social media platforms be regulated like utilities?": "p. ej., ¿Deben regularse las plataformas de redes sociales como servicios públicos?",
        "Create Debate": "Crear debate",
        "Filter topics...": "Filtrar temas...",
        "Newest": "Más recientes",
        "Oldest": "Más antiguos",
        "A → Z": "A → Z",
        "Z → A": "Z → A",
        "Created:": "Creado:",
        "View": "Ver",
        "Close Debate": "Cerrar debate",
        "No open debates yet.": "Aún no hay debates abiertos.",
        "No closed debates yet.": "Aún no hay debates cerrados.",
        "Debate Topic": "Tema del debate",
        "Share Your Thoughts": "Comparte tu opinión",
        "Your Post": "Tu publicación",
        "Write a clear, constructive contribution to the debate…": "Escribe una contribución clara y constructiva al debate…",
        "Suggested length:": "Longitud sugerida:",
        "50–500 words": "50–500 palabras",
        "/2000": "/2000",
        "Please revise your post to remove disallowed terms and ensure it's on-topic.": "Revisa tu publicación para eliminar términos no permitidos y asegurarte de que sea relevante.",
        "Back to Debate": "Volver al debate",
        "Submit Post": "Publicar",
        "Please add a bit more detail (at least ~10 words).": "Añade un poco más de detalle (al menos ~10 palabras).",
        "Please keep your post on-topic and respectful. Posts are visible to others.": "Mantén tu publicación centrada en el tema y con respeto. Otras personas pueden verla.",
        "Stay relevant to": "Mantente relevante para",
        "Support claims with sources when possible.": "Respalda tus afirmaciones con fuentes cuando sea posible.",
        "Use civil language. Critique ideas, not people.": "Usa un lenguaje respetuoso. Critica ideas, no personas.",
        "No hate speech, harassment, or calls for violence. Avoid slurs and personal data.": "No se permite discurso de odio, acoso ni llamados a la violencia. Evita insultos y datos personales.",
        "No unrelated spam or promotional content.": "No se permite spam no relacionado ni contenido promocional.",
        "Add News Article": "Agregar artículo de noticias",
        "Attach a credible source, summarize clearly, and keep it civil.": "Adjunta una fuente creíble, resume con claridad y mantén un tono respetuoso.",
        "We store title, link, summary & content to compute bias scores.": "Guardamos el título, el enlace, el resumen y el contenido para calcular las puntuaciones de sesgo.",
        "Article Title": "Título del artículo",
        "Enter the article headline…": "Introduce el titular del artículo…",
        "Keep it faithful to the original headline.": "Mantén fidelidad al titular original.",
        "Article Link": "Enlace del artículo",
        "https://example.com/news/article": "https://example.com/news/article",
        "We'll try to pull the full text from the URL for you to review and edit.": "Intentaremos extraer el texto completo desde la URL para que puedas revisarlo y editarlo.",
        "Extract Content": "Extraer contenido",
        "Summarize the article in 2–3 sentences…": "Resume el artículo en 2–3 oraciones…",
        "Be neutral and concise; avoid personal opinions here.": "Sé neutral y conciso; evita opiniones personales aquí.",
        "News Content": "Contenido de la noticia",
        "Paste or edit the extracted article text…": "Pega o edita el texto extraído del artículo…",
        "Edit for clarity. Don't include unrelated or harmful content.": "Edita para mayor claridad. No incluyas contenido no relacionado o perjudicial.",
        "Guidelines": "Pautas",
        "Stay on topic and cite credible sources.": "Mantente en el tema y cita fuentes creíbles.",
        "No hate speech, harassment, or personal attacks.": "No se permite discurso de odio, acoso ni ataques personales.",
        "Report misclassified or suspicious sources to an admin.": "Informa a una persona administradora sobre fuentes mal clasificadas o sospechosas.",
        "After submission, bias and stance will be computed automatically.": "Tras el envío, el sesgo y la postura se calcularán automáticamente.",
        "Submit News": "Enviar noticia",
        "Please paste a valid link first.": "Primero pega un enlace válido.",
        "Extracting…": "Extrayendo…",
        "Error:": "Error:",
        "Failed to extract content.": "No se pudo extraer el contenido.",
        "Request failed. Please check the link or try again later.": "La solicitud falló. Verifica el enlace o inténtalo de nuevo más tarde.",
        "Bias • Summary • Transparency": "Sesgo • Resumen • Transparencia",
        "See the story behind the story.": "Ve la historia detrás de la historia.",
        "FairRead analyzes any article for political lean, explains why, and returns a concise summary you can trust.": "FairRead analiza cualquier artículo para detectar su inclinación política, explica por qué y devuelve un resumen conciso en el que puedes confiar.",
        "Analyze an Article": "Analizar un artículo",
        "Explore Features": "Explorar funciones",
        "Private by default • URL · Text · PDF": "Privado por defecto • URL · Texto · PDF",
        "Preview": "Vista previa",
        "Bias · Confidence · Key signals": "Sesgo · Confianza · Señales clave",
        "About": "Acerca de",
        "FairRead explained": "FairRead explicado",
        "FairRead is a lightweight tool for evaluating news articles with clarity and speed. Paste a link, text, or PDF and receive an objective read on where the piece leans.": "FairRead es una herramienta ligera para evaluar artículos de noticias con claridad y rapidez. Pega un enlace, texto o un PDF y obtén una lectura objetiva de la inclinación de la pieza.",
        "Results include a brief rationale so you can see the cues behind the call — not just the label. Your history stays private and helps you understand your own reading patterns over time.": "Los resultados incluyen una breve explicación para que puedas ver las señales detrás de la evaluación, no solo la etiqueta. Tu historial permanece privado y te ayuda a comprender tus propios patrones de lectura con el tiempo.",
        "Bias classification with confidence": "Clasificación de sesgo con nivel de confianza",
        "Evidence-based rationale (framing, sources, wording)": "Justificación basada en evidencia (enfoque, fuentes, redacción)",
        "Concise, source-aware summary": "Resumen conciso y consciente de las fuentes",
        "Personal analytics with privacy by default": "Analítica personal con privacidad por defecto",
        "Capabilities": "Capacidades",
        "A focused toolkit for reading news clearly": "Un conjunto de herramientas enfocado para leer noticias con claridad",
        "Everything you need to judge an article—nothing you don't.": "Todo lo que necesitas para evaluar un artículo, y nada de más.",
        "Bias classification with rationale": "Clasificación de sesgo con explicación",
        "Left / center / right paired with the specific cues that informed the call (framing, sources, wording).": "Izquierda / centro / derecha junto con las señales específicas que sustentan la evaluación (enfoque, fuentes, redacción).",
        "Clear, skimmable summaries that preserve context and map claims to evidence.": "Resúmenes claros y fáciles de revisar que preservan el contexto y vinculan afirmaciones con evidencia.",
        "Learning features": "Funciones de aprendizaje",
        "Study article terms": "Estudiar términos del artículo",
        "Open the Learn tab after analysis to review vocabulary, idioms, and grammar in the article language with English support.": "Abre la pestaña Learn después del análisis para revisar vocabulario, modismos y gramática en el idioma del artículo con apoyo en inglés.",
        "Learning mode": "Modo de aprendizaje",
        "Practice terms from your articles and keep them in the article language.": "Practica los términos de tus artículos y consérvalos en el idioma del artículo.",
        "Private reading analytics": "Analítica privada de lectura",
        "See trends in outlets and perspectives over time—stored locally by default.": "Observa tendencias en medios y perspectivas a lo largo del tiempo, almacenadas localmente por defecto.",
        "Flexible inputs": "Entradas flexibles",
        "Analyze URLs, pasted text, or PDFs. Robust parsing for long-form pieces.": "Analiza URL, texto pegado o PDF. Ofrece un procesamiento sólido para piezas extensas.",
        "Quality & controls": "Calidad y controles",
        "Deterministic modes for consistency and clear versioned outputs for sharing.": "Modos deterministas para mantener la consistencia y salidas versionadas claras para compartir.",
        "Getting Started": "Primeros pasos",
        "How to Use FairRead": "Cómo usar FairRead",
        "Follow three quick steps to analyze any news article with clarity and transparency.": "Sigue tres pasos rápidos para analizar cualquier artículo de noticias con claridad y transparencia.",
        "1. Provide the article": "1. Proporciona el artículo",
        "Enter a link, paste the text, or upload a PDF.": "Introduce un enlace, pega el texto o sube un PDF.",
        "2. Let AI analyze": "2. Deja que la IA analice",
        "FairRead detects political bias, highlights key signals, and summarizes the piece.": "FairRead detecta el sesgo político, resalta las señales clave y resume la pieza.",
        "3. Review insights": "3. Revisa los resultados",
        "See the bias label, rationale, and a concise summary you can trust.": "Consulta la etiqueta de sesgo, la explicación y un resumen conciso en el que puedes confiar.",
        "Community": "Comunidad",
        "Discuss, compare, and learn together": "Debatir, comparar y aprender juntos",
        "Join focused debate rooms on live topics, compare evidence, and see how perspectives shift—without sacrificing civility or privacy.": "Únete a salas de debate enfocadas en temas actuales, compara evidencias y observa cómo cambian las perspectivas, sin sacrificar la cordialidad ni la privacidad.",
        "Explore Debate Rooms": "Explorar salas de debate",
        "Topic-Focused Rooms": "Salas centradas en temas",
        "Join curated rooms on specific policy issues. Keep discussions on track with structured prompts and timeboxed rounds.": "Únete a salas seleccionadas sobre cuestiones específicas de política pública. Mantén las conversaciones enfocadas con indicaciones estructuradas y rondas con tiempo definido.",
        "Weekly prompts and summaries": "Prompts y resúmenes semanales",
        "Invite-only or public access": "Acceso por invitación o público",
        "Evidence-Linked Posts": "Publicaciones vinculadas a evidencia",
        "Back claims with links or PDFs. FairRead highlights bias signals in cited content so participants can assess sources quickly.": "Respalda tus afirmaciones con enlaces o PDF. FairRead destaca señales de sesgo en el contenido citado para que las personas participantes evalúen las fuentes rápidamente.",
        "Inline article analysis": "Análisis de artículos en línea",
        "Quote and counter-quote threads": "Hilos de cita y contracita",
        "Civility & Privacy": "Civilidad y privacidad",
        "Moderation tools and private rooms reduce noise. Participation history stays local by default; share only what you choose.": "Las herramientas de moderación y las salas privadas reducen el ruido. El historial de participación permanece local por defecto; comparte solo lo que elijas.",
        "Report & mute controls": "Controles de denuncia y silencio",
        "Privacy-first analytics": "Analítica centrada en la privacidad",
        "Weekly Topic": "Tema semanal",
        "Each week introduces a new debate prompt with a short neutral brief to frame the discussion.": "Cada semana se presenta una nueva propuesta de debate con un breve resumen neutral para enmarcar la discusión.",
        "Structured Rounds": "Rondas estructuradas",
        "Opening statements, evidence posts, and closing remarks keep conversations concise and comparable.": "Las declaraciones iniciales, las publicaciones con evidencia y las conclusiones mantienen las conversaciones concisas y comparables.",
        "Outcome Snapshot": "Resumen del resultado",
        "See a neutral wrap-up: main claims, strongest evidence cited, and perspective shift over the week.": "Consulta un cierre neutral: afirmaciones principales, evidencia más sólida citada y cambio de perspectiva a lo largo de la semana.",
        "© 2024~2026 FairRead. All Rights Reserved.": "© 2024~2026 FairRead. Todos los derechos reservados.",
        "Learn from this article": "Aprende de este artículo",
        "Learning Term Review": "Revisión de términos de aprendizaje",
        "Review extracted terms by timeframe.": "Revisa los términos extraídos por período.",
        "Day": "Día",
        "Week": "Semana",
        "Month": "Mes",
        "No learning terms yet": "Aún no hay términos de aprendizaje",
        "Terms from your learned articles will appear here.": "Los términos de tus artículos aprendidos aparecerán aquí.",
        "Week of": "Semana de",
        "All Terms": "Todos los términos",
        "Learned": "Aprendido",
        "Not learned": "No aprendido",
        "Learning Terms": "Términos de aprendizaje",
        "Click any term to see details": "Haz clic en cualquier término para ver los detalles",
        "Vocabulary": "Vocabulario",
        "Idiom": "Modismo",
        "Grammar": "Patrón gramatical",
        "Beginner": "Principiante",
        "Intermediate": "Intermedio",
        "Advanced": "Avanzado",
        "Definition": "Definición",
        "Example": "Ejemplo",
        "Part of Speech": "Parte del discurso",
        "Difficulty": "Dificultad",
        "Grammar Note": "Nota de gramática",
        "Your language": "Tu idioma",
        "Article language": "Idioma del artículo",
        "Total Terms": "Términos totales",
        "Back to Analysis": "Volver al análisis",
        "Generating learning terms...": "Generando términos de aprendizaje...",
        "Extracting learning terms...": "Extrayendo términos de aprendizaje...",
        "This usually takes 10-30 seconds.": "Esto suele tardar entre 10 y 30 segundos.",
        "Still working...": "Todavía trabajando...",
        "If this takes too long, please refresh.": "Si esto tarda demasiado, por favor recarga.",
        "Extraction is taking longer than expected.": "La extracción está tardando más de lo esperado.",
        "Failed to generate learning terms.": "No se pudieron generar los términos de aprendizaje.",
    },
    "zh": {
        "Home": "首页",
        "News": "新闻",
        "Learn": "学习",
        "Debate": "辩论",
        "Profile": "个人资料",
        "Statistics": "统计",
        "Login": "登录",
        "Logout": "登出",
        "Bias Classification": "倾向分类",
        "Summary": "摘要",
        "Keywords": "关键词",
        "Reason": "理由",
        "Username": "用户名",
        "Password": "密码",
        "Not a member?": "还没有账号？",
        "Sign up": "注册",
        "Select your gender": "请选择性别",
        "Select your birthday": "请选择生日",
        "Male": "男性",
        "Female": "女性",
        "Other": "其他",
        "Register": "注册",
        "Registration complete": "注册完成",
        "Your account was created successfully. You can now sign in.": "您的账号已成功创建。现在可以登录。",
        "Go to Login": "前往登录",
        "Already have an account?": "已经有账号？",
        "Sign in": "登录",
        "News Classifier": "新闻分类器",
        "We will classify the news for you!": "我们将为您分析新闻倾向！",
        "How to use": "使用方法",
        "Attach File": "附加文件",
        "Paste or type article text or notes here...": "在此粘贴或输入文章正文或笔记...",
        "Class": "类别",
        "Bias Class": "倾向类别",
        "Bias Class:": "倾向类别：",
        "Bias Scores": "倾向分数",
        "Bias Scores:": "倾向分数：",
        "Left": "左翼",
        "Center": "中立",
        "Right": "右翼",
        "Left:": "左翼：",
        "Center:": "中间：",
        "Right:": "右翼：",
        "Not analyzed yet": "尚未分析",
        "Reason for Bias": "倾向原因",
        "Analysis pending...": "分析中...",
        "News Summary": "新闻摘要",
        "Summary will appear here...": "摘要将显示在这里...",
        "Keywords will be shown here...": "关键词将显示在这里...",
        "How to use the News Classifier": "如何使用新闻分类器",
        "Ways to submit": "提交方式",
        "Paste text": "粘贴文本",
        "Paste any article text or your notes, then press Enter or click the send icon.": "粘贴任意文章文本或您的笔记，然后按 Enter 键或点击发送图标。",
        "Paste a link": "粘贴链接",
        "Drop an article URL. We'll fetch its content when possible and analyze it.": "输入文章 URL。若可获取内容，我们会抓取并进行分析。",
        "Upload a file": "上传文件",
        "PDF or DOCX supported. If a file is attached, it takes priority over typed text.": "支持 PDF 或 DOCX。如果附加了文件，将优先处理文件而非输入文本。",
        "What you'll see": "您将看到",
        "Left / Center / Right Scores": "左 / 中 / 右分数",
        "Tips & limits": "提示与限制",
        "Filenames should be English letters/numbers only": "文件名只能使用英文字母和数字",
        "For paywalled pages, paste the article text or upload a PDF.": "对于付费墙页面，请粘贴文章正文或上传 PDF。",
        "Very long documents can take longer to process.": "文档过长时，处理时间可能更长。",
        "If content extraction fails, try another link or paste the text directly.": "如果内容提取失败，请尝试其他链接或直接粘贴文本。",
        "We analyze your input and show results on the right.": "我们会分析您的输入，并在右侧显示结果。",
        "Got it": "知道了",
        "Hello! You can copy and paste the news text or link, or upload a PDF file. The analysis results will appear on the right.": "你好！你可以复制粘贴新闻文本或链接，或上传PDF文件。分析结果将显示在右侧。",
        "Analyzing, please wait...": "正在分析，请稍候...",
        "Error fetching URL": "获取 URL 出错",
        "Unable to fetch article (HTTP error). Website may be blocking automated access.": "无法获取文章（HTTP 错误）。网站可能阻止了自动访问。",
        "This article appears to be behind a paywall. Please try copying the text directly or accessing via an archive service.": "此文章似乎在付费墙后。请尝试直接复制文本或通过存档服务访问。",
        "Request timed out. The website is taking too long to respond.": "请求超时。网站响应时间过长。",
        "Connection error. Please check the URL and your internet connection.": "连接错误。请检查 URL 和您的互联网连接。",
        "Unable to extract article content. The website structure may not be supported.": "无法提取文章内容。网站结构可能不受支持。",
        "Article text is too short or could not be extracted.": "文章文本过短或无法提取。",
        "Please rename the file using only English letters, numbers, spaces, underscores, hyphens, and dots (e.g., news_article_2025.pdf).": "请将文件重命名为仅使用英文字母、数字、空格、下划线、连字符和点（例如：news_article_2025.pdf）。",
        "Done Processing. Please check the right side.": "处理完成。请查看右侧结果。",
        "Please attach a file or enter a message.": "请附加文件或输入消息。",
        "Filename not allowed. Use only English letters, numbers, spaces, underscores, hyphens, and dots.": "文件名不符合要求。请仅使用英文字母、数字、空格、下划线、连字符和点。",
        "My Data": "我的数据",
        "No data yet": "暂无数据",
        "Classify your first article to see bias distribution and topics here.": "先分析您的第一篇文章，即可在此查看倾向分布和主题。",
        "Start classifying": "开始分析",
        "Bias Distribution": "倾向分布",
        "Average across your submissions": "基于您提交内容的平均值",
        "Top Topics": "热门主题",
        "Most frequent keywords": "最常见关键词",
        "Recent Classifications": "最近分类",
        "Prev": "上一页",
        "Next": "下一页",
        "No recent items": "暂无近期记录",
        "Your latest classifications will appear here after you analyze an article.": "分析文章后，您最近的分类结果将显示在这里。",
        "Analyze an article": "分析一篇文章",
        "Class:": "类别：",
        "Mentions": "提及次数",
        "Total Users": "用户总数",
        "Active Users (30d)": "近30天活跃用户",
        "Total News": "新闻总数",
        "Recent News (30d)": "近30天新闻",
        "Chatbot Usage (Last 7 Days)": "最近7天聊天机器人使用情况",
        "Daily requests": "每日请求数",
        "Monthly Chatbot Usage": "每月聊天机器人使用情况",
        "By month": "按月",
        "User Growth": "用户增长",
        "Accounts over time": "账号增长趋势",
        "Top Keywords": "热门关键词",
        "Most frequent": "最常见",
        "Daily User Sessions": "每日用户会话",
        "Last 7 days": "最近7天",
        "Average Bias Scores": "平均倾向分数",
        "All": "全部",
        "Chatbot Usage": "聊天机器人使用情况",
        "Sessions": "会话数",
        "Users": "用户数",
        "Created on": "创建于",
        "Back to Debates": "返回辩论列表",
        "Create Post": "发布帖子",
        "Add Related News": "添加相关文章",
        "Discussion": "讨论",
        "Delete": "删除",
        "Like": "点赞",
        "Comments": "评论",
        "Write a comment…": "写下评论…",
        "No posts yet. Be the first to contribute to the discussion.": "还没有帖子。成为第一个参与讨论的人吧。",
        "Related News": "相关新闻",
        "More": "更多",
        "Open original article": "打开原文",
        "Bias & Scores": "倾向与分数",
        "Classification:": "分类：",
        "Cast your view on this article's bias to see the full breakdown.": "发表您对这篇文章倾向的看法，即可查看完整分解。",
        "Read Full Article": "阅读全文",
        "Close": "关闭",
        "What is your opinion about this article's bias?": "您如何看待这篇文章的倾向？",
        "No news articles have been added yet.": "还未添加新闻文章。",
        "Delete this post? This cannot be undone.": "删除此帖子？此操作无法撤销。",
        "Delete this news item? This cannot be undone.": "删除这条新闻？此操作无法撤销。",
        "Debates": "辩论",
        "Open": "进行中",
        "Open:": "进行中：",
        "Closed": "已关闭",
        "Closed:": "已关闭：",
        "e.g., Should social media platforms be regulated like utilities?": "例如：社交媒体平台是否应像公用事业一样受到监管？",
        "Create Debate": "创建辩论",
        "Filter topics...": "筛选主题...",
        "Newest": "最新",
        "Oldest": "最早",
        "A → Z": "A → Z",
        "Z → A": "Z → A",
        "Created:": "创建时间：",
        "View": "查看",
        "Close Debate": "关闭辩论",
        "No open debates yet.": "还没有进行中的辩论。",
        "No closed debates yet.": "还没有已关闭的辩论。",
        "Debate Topic": "辩论主题",
        "Share Your Thoughts": "分享您的看法",
        "Your Post": "您的帖子",
        "Write a clear, constructive contribution to the debate…": "写下清晰且建设性的讨论内容…",
        "Suggested length:": "建议长度：",
        "50–500 words": "50–500 个词",
        "/2000": "/2000",
        "Please revise your post to remove disallowed terms and ensure it's on-topic.": "请修改您的帖子，删除不允许的用语，并确保内容与主题相关。",
        "Back to Debate": "返回辩论",
        "Submit Post": "提交帖子",
        "Please add a bit more detail (at least ~10 words).": "请补充更多细节（至少约 10 个词）。",
        "Please keep your post on-topic and respectful. Posts are visible to others.": "请确保您的帖子切题且尊重他人。帖子对其他人可见。",
        "Stay relevant to": "请围绕以下主题",
        "Support claims with sources when possible.": "如有可能，请用来源支持您的观点。",
        "Use civil language. Critique ideas, not people.": "请使用文明用语。批评观点，而非针对个人。",
        "No hate speech, harassment, or calls for violence. Avoid slurs and personal data.": "禁止仇恨言论、骚扰或鼓动暴力。请避免使用侮辱性词语和个人信息。",
        "No unrelated spam or promotional content.": "禁止发布无关垃圾信息或推广内容。",
        "Add News Article": "添加新闻文章",
        "Attach a credible source, summarize clearly, and keep it civil.": "请附上可信来源，清晰概述内容，并保持文明表达。",
        "We store title, link, summary & content to compute bias scores.": "我们会存储标题、链接、摘要和内容，以计算倾向分数。",
        "Article Title": "文章标题",
        "Enter the article headline…": "输入文章标题…",
        "Keep it faithful to the original headline.": "保持与原标题一致。",
        "Article Link": "文章链接",
        "https://example.com/news/article": "https://example.com/news/article",
        "We'll try to pull the full text from the URL for you to review and edit.": "我们会尝试从该 URL 提取全文，供您查看和编辑。",
        "Extract Content": "提取内容",
        "Summarize the article in 2–3 sentences…": "请用 2–3 句话概述文章…",
        "Be neutral and concise; avoid personal opinions here.": "请保持中立简洁；此处避免加入个人观点。",
        "News Content": "新闻内容",
        "Paste or edit the extracted article text…": "粘贴或编辑提取出的文章文本…",
        "Edit for clarity. Don't include unrelated or harmful content.": "请为清晰度进行编辑。不要包含无关或有害内容。",
        "Guidelines": "指南",
        "Stay on topic and cite credible sources.": "请围绕主题并引用可信来源。",
        "No hate speech, harassment, or personal attacks.": "禁止仇恨言论、骚扰或人身攻击。",
        "Report misclassified or suspicious sources to an admin.": "如发现误分类或可疑来源，请向管理员报告。",
        "After submission, bias and stance will be computed automatically.": "提交后，倾向和立场将自动计算。",
        "Submit News": "提交新闻",
        "Please paste a valid link first.": "请先粘贴有效链接。",
        "Extracting…": "正在提取…",
        "Error:": "错误：",
        "Failed to extract content.": "内容提取失败。",
        "Request failed. Please check the link or try again later.": "请求失败。请检查链接或稍后重试。",
        "Bias • Summary • Transparency": "倾向 • 摘要 • 透明度",
        "See the story behind the story.": "看见新闻背后的脉络。",
        "FairRead analyzes any article for political lean, explains why, and returns a concise summary you can trust.": "FairRead 可分析任意文章的政治倾向，解释原因，并返回值得信赖的简明摘要。",
        "Analyze an Article": "分析文章",
        "Explore Features": "探索功能",
        "Private by default • URL · Text · PDF": "默认私密 • URL · 文本 · PDF",
        "Preview": "预览",
        "Bias · Confidence · Key signals": "倾向 · 置信度 · 关键信号",
        "About": "关于",
        "FairRead explained": "FairRead 介绍",
        "FairRead is a lightweight tool for evaluating news articles with clarity and speed. Paste a link, text, or PDF and receive an objective read on where the piece leans.": "FairRead 是一款轻量工具，可快速清晰地评估新闻文章。粘贴链接、文本或 PDF，即可获得对文章倾向的客观判断。",
        "Results include a brief rationale so you can see the cues behind the call — not just the label. Your history stays private and helps you understand your own reading patterns over time.": "结果包含简要说明，让您看到判断背后的线索，而不仅仅是标签。您的历史记录默认保持私密，并帮助您长期了解自己的阅读模式。",
        "Bias classification with confidence": "带置信度的倾向分类",
        "Evidence-based rationale (framing, sources, wording)": "基于证据的说明（框架、来源、措辞）",
        "Concise, source-aware summary": "简洁且关注来源的摘要",
        "Personal analytics with privacy by default": "默认私密的个人分析",
        "Capabilities": "功能",
        "A focused toolkit for reading news clearly": "一套专注于清晰阅读新闻的工具",
        "Everything you need to judge an article—nothing you don't.": "判断一篇文章所需的一切功能，恰到好处。",
        "Bias classification with rationale": "带说明的倾向分类",
        "Left / center / right paired with the specific cues that informed the call (framing, sources, wording).": "左 / 中 / 右结论会结合具体线索展示（框架、来源、措辞）。",
        "Clear, skimmable summaries that preserve context and map claims to evidence.": "清晰易扫读的摘要，在保留语境的同时将观点对应到证据。",
        "Learning features": "学习功能",
        "Study article terms": "学习文章术语",
        "Open the Learn tab after analysis to review vocabulary, idioms, and grammar in the article language with English support.": "分析后打开 Learn 选项卡，在英文辅助下复习文章语言中的词汇、习语和语法。",
        "Learning mode": "学习模式",
        "Practice terms from your articles and keep them in the article language.": "练习你文章中的术语，并保持为文章原语言。",
        "Private reading analytics": "私密阅读分析",
        "See trends in outlets and perspectives over time—stored locally by default.": "查看媒体来源和观点的长期趋势——默认本地存储。",
        "Flexible inputs": "灵活输入",
        "Analyze URLs, pasted text, or PDFs. Robust parsing for long-form pieces.": "支持分析 URL、粘贴文本或 PDF，并能稳健解析长篇内容。",
        "Quality & controls": "质量与控制",
        "Deterministic modes for consistency and clear versioned outputs for sharing.": "确定性模式保证结果一致，并提供清晰的版本化输出，便于分享。",
        "Getting Started": "快速开始",
        "How to Use FairRead": "如何使用 FairRead",
        "Follow three quick steps to analyze any news article with clarity and transparency.": "只需三个简单步骤，即可清晰透明地分析任何新闻文章。",
        "1. Provide the article": "1. 提供文章",
        "Enter a link, paste the text, or upload a PDF.": "输入链接、粘贴文本或上传 PDF。",
        "2. Let AI analyze": "2. 让 AI 分析",
        "FairRead detects political bias, highlights key signals, and summarizes the piece.": "FairRead 会识别政治倾向、突出关键信号，并总结文章内容。",
        "3. Review insights": "3. 查看结果",
        "See the bias label, rationale, and a concise summary you can trust.": "查看倾向标签、分析理由以及值得信赖的简洁摘要。",
        "Community": "社区",
        "Discuss, compare, and learn together": "一起讨论、比较与学习",
        "Join focused debate rooms on live topics, compare evidence, and see how perspectives shift—without sacrificing civility or privacy.": "加入围绕热点话题的专题讨论室，比较证据，观察观点如何变化——同时不牺牲礼貌与隐私。",
        "Explore Debate Rooms": "探索辩论室",
        "Topic-Focused Rooms": "主题讨论室",
        "Join curated rooms on specific policy issues. Keep discussions on track with structured prompts and timeboxed rounds.": "加入围绕特定政策议题精心策划的讨论室。通过结构化提示和限时轮次，让讨论保持聚焦。",
        "Weekly prompts and summaries": "每周提示与摘要",
        "Invite-only or public access": "仅限邀请或公开访问",
        "Evidence-Linked Posts": "证据关联帖子",
        "Back claims with links or PDFs. FairRead highlights bias signals in cited content so participants can assess sources quickly.": "用链接或 PDF 支持您的观点。FairRead 会突出引用内容中的倾向信号，帮助参与者快速评估来源。",
        "Inline article analysis": "行内文章分析",
        "Quote and counter-quote threads": "引用与反驳线程",
        "Civility & Privacy": "文明与隐私",
        "Moderation tools and private rooms reduce noise. Participation history stays local by default; share only what you choose.": "审核工具和私密房间可减少噪音。参与历史默认保存在本地；只分享您愿意分享的内容。",
        "Report & mute controls": "举报与静音控制",
        "Privacy-first analytics": "隐私优先的分析",
        "Weekly Topic": "每周主题",
        "Each week introduces a new debate prompt with a short neutral brief to frame the discussion.": "每周都会推出新的辩题，并附上简短中立的导语来框定讨论。",
        "Structured Rounds": "结构化轮次",
        "Opening statements, evidence posts, and closing remarks keep conversations concise and comparable.": "开场陈述、证据帖子和总结发言让讨论保持简洁且便于比较。",
        "Outcome Snapshot": "结果概览",
        "See a neutral wrap-up: main claims, strongest evidence cited, and perspective shift over the week.": "查看中立总结：主要观点、最有力的引用证据，以及一周内观点的变化。",
        "© 2024~2026 FairRead. All Rights Reserved.": "© 2024~2026 FairRead. 版权所有。",
        "Learn from this article": "从这篇文章中学习",
        "Learning Term Review": "学习术语回顾",
        "Review extracted terms by timeframe.": "按时间范围查看提取的术语。",
        "Day": "日",
        "Week": "周",
        "Month": "月",
        "No learning terms yet": "还没有学习术语",
        "Terms from your learned articles will appear here.": "你已学习文章中的术语会显示在这里。",
        "Week of": "当周",
        "All Terms": "全部术语",
        "Learned": "已学习",
        "Not learned": "未学习",
        "Learning Terms": "学习术语",
        "Click any term to see details": "单击任何术语以查看详情",
        "Vocabulary": "词汇",
        "Idiom": "习语",
        "Grammar": "语法模式",
        "Beginner": "初级",
        "Intermediate": "中级",
        "Advanced": "高级",
        "Definition": "定义",
        "Example": "例子",
        "Part of Speech": "词类",
        "Difficulty": "难度",
        "Grammar Note": "语法说明",
        "Your language": "你的语言",
        "Article language": "文章语言",
        "Total Terms": "总术语数",
        "Back to Analysis": "返回分析",
        "Generating learning terms...": "正在生成学习术语...",
        "Extracting learning terms...": "正在提取学习术语...",
        "This usually takes 10-30 seconds.": "通常需要 10-30 秒。",
        "Still working...": "仍在处理中...",
        "If this takes too long, please refresh.": "如果耗时过长，请刷新页面。",
        "Extraction is taking longer than expected.": "提取时间比预期更长。",
        "Failed to generate learning terms.": "生成学习术语失败。",
    },
    "ko": {
        "Home": "홈",
        "News": "뉴스",
        "Learn": "학습",
        "Debate": "토론",
        "Profile": "프로필",
        "Statistics": "통계",
        "Login": "로그인",
        "Logout": "로그아웃",
        "Bias Classification": "편향 분류",
        "Summary": "요약",
        "Keywords": "키워드",
        "Reason": "이유",
        "Username": "사용자명",
        "Password": "비밀번호",
        "Not a member?": "아직 계정이 없으신가요?",
        "Sign up": "회원가입",
        "Select your gender": "성별을 선택하세요",
        "Select your birthday": "생년월일을 선택하세요",
        "Male": "남성",
        "Female": "여성",
        "Other": "기타",
        "Register": "가입하기",
        "Registration complete": "가입 완료",
        "Your account was created successfully. You can now sign in.": "계정이 성공적으로 생성되었습니다. 이제 로그인하실 수 있습니다.",
        "Go to Login": "로그인으로 이동",
        "Already have an account?": "이미 계정이 있으신가요?",
        "Sign in": "로그인",
        "News Classifier": "뉴스 분류기",
        "We will classify the news for you!": "뉴스 성향을 분석해 드립니다!",
        "How to use": "사용 방법",
        "Attach File": "파일 첨부",
        "Paste or type article text or notes here...": "기사 본문이나 메모를 여기에 붙여넣거나 입력하세요...",
        "Class": "분류",
        "Bias Class": "편향 분류",
        "Bias Class:": "편향 분류:",
        "Bias Scores": "편향 점수",
        "Bias Scores:": "편향 점수:",
        "Left": "좌파",
        "Center": "중도",
        "Right": "우파",
        "Left:": "좌파:",
        "Center:": "중도:",
        "Right:": "우파:",
        "Not analyzed yet": "아직 분석되지 않았습니다",
        "Reason for Bias": "편향 이유",
        "Analysis pending...": "분석 중...",
        "News Summary": "뉴스 요약",
        "Summary will appear here...": "요약이 여기에 표시됩니다...",
        "Keywords will be shown here...": "키워드가 여기에 표시됩니다...",
        "How to use the News Classifier": "뉴스 분류기 사용 방법",
        "Ways to submit": "제출 방법",
        "Paste text": "텍스트 붙여넣기",
        "Paste any article text or your notes, then press Enter or click the send icon.": "기사 본문이나 메모를 붙여넣은 뒤 Enter를 누르거나 보내기 아이콘을 클릭하세요.",
        "Paste a link": "링크 붙여넣기",
        "Drop an article URL. We'll fetch its content when possible and analyze it.": "기사 URL을 입력하세요. 가능하면 본문을 가져와 분석합니다.",
        "Upload a file": "파일 업로드",
        "PDF or DOCX supported. If a file is attached, it takes priority over typed text.": "PDF 또는 DOCX를 지원합니다. 파일이 첨부되면 입력한 텍스트보다 우선 처리됩니다.",
        "What you'll see": "표시되는 정보",
        "Left / Center / Right Scores": "좌 / 중 / 우 점수",
        "Tips & limits": "안내 및 제한사항",
        "Filenames should be English letters/numbers only": "파일 이름은 영문자와 숫자만 사용하세요",
        "For paywalled pages, paste the article text or upload a PDF.": "유료 구독이 필요한 페이지는 기사 본문을 붙여넣거나 PDF를 업로드해 주세요.",
        "Very long documents can take longer to process.": "매우 긴 문서는 처리 시간이 더 오래 걸릴 수 있습니다.",
        "If content extraction fails, try another link or paste the text directly.": "내용 추출에 실패하면 다른 링크를 시도하거나 본문을 직접 붙여넣어 주세요.",
        "We analyze your input and show results on the right.": "입력하신 내용을 분석한 뒤 결과를 오른쪽에 표시합니다.",
        "Got it": "확인했습니다",
        "Hello! You can copy and paste the news text or link, or upload a PDF file. The analysis results will appear on the right.": "안녕하세요! 뉴스 텍스트나 링크를 복사해서 붙여넣거나 PDF 파일을 업로드할 수 있습니다. 분석 결과는 오른쪽에 표시됩니다.",
        "Analyzing, please wait...": "분석 중입니다. 잠시만 기다려 주세요...",
        "Error fetching URL": "URL 가져오기 오류",
        "Unable to fetch article (HTTP error). Website may be blocking automated access.": "기사를 가져올 수 없습니다(HTTP 오류). 웹사이트에서 자동화된 액세스를 차단할 수 있습니다.",
        "This article appears to be behind a paywall. Please try copying the text directly or accessing via an archive service.": "이 기사는 유료 구독이 필요한 것 같습니다. 텍스트를 직접 복사하거나 아카이브 서비스를 통해 액세스해 보세요.",
        "Request timed out. The website is taking too long to respond.": "요청 시간 초과. 웹사이트의 응답이 너무 오래 걸립니다.",
        "Connection error. Please check the URL and your internet connection.": "연결 오류. URL과 인터넷 연결을 확인해 주세요.",
        "Unable to extract article content. The website structure may not be supported.": "기사 내용을 추출할 수 없습니다. 웹사이트 구조가 지원되지 않을 수 있습니다.",
        "Article text is too short or could not be extracted.": "기사 텍스트가 너무 짧거나 추출할 수 없습니다.",
        "Please rename the file using only English letters, numbers, spaces, underscores, hyphens, and dots (e.g., news_article_2025.pdf).": "파일 이름은 영문자, 숫자, 공백, 밑줄, 하이픈, 마침표만 사용하여 다시 지정해 주세요(예: news_article_2025.pdf).",
        "Done Processing. Please check the right side.": "처리가 완료되었습니다. 오른쪽 결과를 확인해 주세요.",
        "Please attach a file or enter a message.": "파일을 첨부하거나 메시지를 입력해 주세요.",
        "Filename not allowed. Use only English letters, numbers, spaces, underscores, hyphens, and dots.": "허용되지 않는 파일 이름입니다. 영문자, 숫자, 공백, 밑줄, 하이픈, 마침표만 사용해 주세요.",
        "My Data": "내 데이터",
        "No data yet": "아직 데이터가 없습니다",
        "Classify your first article to see bias distribution and topics here.": "첫 번째 기사를 분석하면 여기에서 편향 분포와 주제를 확인할 수 있습니다.",
        "Start classifying": "분석 시작",
        "Bias Distribution": "편향 분포",
        "Average across your submissions": "제출물 평균",
        "Top Topics": "주요 주제",
        "Most frequent keywords": "가장 자주 나온 키워드",
        "Recent Classifications": "최근 분류 결과",
        "Prev": "이전",
        "Next": "다음",
        "No recent items": "최근 항목이 없습니다",
        "Your latest classifications will appear here after you analyze an article.": "기사를 분석하면 최근 분류 결과가 여기에 표시됩니다.",
        "Analyze an article": "기사 분석하기",
        "Class:": "분류:",
        "Mentions": "언급 수",
        "Total Users": "총 사용자 수",
        "Active Users (30d)": "최근 30일 활성 사용자",
        "Total News": "총 뉴스 수",
        "Recent News (30d)": "최근 30일 뉴스",
        "Chatbot Usage (Last 7 Days)": "최근 7일 챗봇 사용량",
        "Daily requests": "일일 요청 수",
        "Monthly Chatbot Usage": "월별 챗봇 사용량",
        "By month": "월별",
        "User Growth": "사용자 증가",
        "Accounts over time": "기간별 계정 수",
        "Top Keywords": "상위 키워드",
        "Most frequent": "가장 빈번한 항목",
        "Daily User Sessions": "일일 사용자 세션",
        "Last 7 days": "최근 7일",
        "Average Bias Scores": "평균 편향 점수",
        "All": "전체",
        "Chatbot Usage": "챗봇 사용량",
        "Sessions": "세션",
        "Users": "사용자",
        "Created on": "생성일",
        "Back to Debates": "토론 목록으로",
        "Create Post": "게시글 작성",
        "Add Related News": "관련 뉴스 추가",
        "Discussion": "토론",
        "Delete": "삭제",
        "Like": "좋아요",
        "Comments": "댓글",
        "Write a comment…": "댓글을 작성하세요…",
        "No posts yet. Be the first to contribute to the discussion.": "아직 게시글이 없습니다. 첫 번째로 토론에 참여해 보세요.",
        "Related News": "관련 뉴스",
        "More": "더보기",
        "Open original article": "원문 기사 열기",
        "Bias & Scores": "편향 및 점수",
        "Classification:": "분류:",
        "Cast your view on this article's bias to see the full breakdown.": "이 기사 편향에 대한 의견을 남기면 전체 분석 결과를 볼 수 있습니다.",
        "Read Full Article": "기사 전체 읽기",
        "Close": "닫기",
        "What is your opinion about this article's bias?": "이 기사 편향에 대해 어떻게 생각하시나요?",
        "No news articles have been added yet.": "아직 추가된 뉴스 기사가 없습니다.",
        "Delete this post? This cannot be undone.": "이 게시글을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
        "Delete this news item? This cannot be undone.": "이 뉴스 항목을 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.",
        "Debates": "토론",
        "Open": "진행 중",
        "Open:": "진행 중:",
        "Closed": "종료됨",
        "Closed:": "종료됨:",
        "e.g., Should social media platforms be regulated like utilities?": "예: 소셜 미디어 플랫폼을 공공요금 서비스처럼 규제해야 할까요?",
        "Create Debate": "토론 생성",
        "Filter topics...": "주제 필터...",
        "Newest": "최신순",
        "Oldest": "오래된순",
        "A → Z": "A → Z",
        "Z → A": "Z → A",
        "Created:": "생성일:",
        "View": "보기",
        "Close Debate": "토론 종료",
        "No open debates yet.": "진행 중인 토론이 아직 없습니다.",
        "No closed debates yet.": "종료된 토론이 아직 없습니다.",
        "Debate Topic": "토론 주제",
        "Share Your Thoughts": "의견을 공유해 주세요",
        "Your Post": "내 게시글",
        "Write a clear, constructive contribution to the debate…": "명확하고 건설적인 의견을 작성해 주세요…",
        "Suggested length:": "권장 분량:",
        "50–500 words": "50~500단어",
        "/2000": "/2000",
        "Please revise your post to remove disallowed terms and ensure it's on-topic.": "허용되지 않는 표현을 제거하고 주제에 맞도록 게시글을 수정해 주세요.",
        "Back to Debate": "토론으로 돌아가기",
        "Submit Post": "게시글 등록",
        "Please add a bit more detail (at least ~10 words).": "내용을 조금 더 보완해 주세요(최소 약 10단어).",
        "Please keep your post on-topic and respectful. Posts are visible to others.": "게시글은 주제에 맞고 예의를 지켜 작성해 주세요. 다른 사용자에게 공개됩니다.",
        "Stay relevant to": "다음 주제와 관련되게 작성해 주세요",
        "Support claims with sources when possible.": "가능하면 출처를 통해 주장을 뒷받침해 주세요.",
        "Use civil language. Critique ideas, not people.": "정중한 표현을 사용해 주세요. 사람보다 의견을 비판하세요.",
        "No hate speech, harassment, or calls for violence. Avoid slurs and personal data.": "혐오 발언, 괴롭힘, 폭력 선동은 허용되지 않습니다. 비하 표현과 개인정보는 피해주세요.",
        "No unrelated spam or promotional content.": "관련 없는 스팸이나 홍보성 콘텐츠는 허용되지 않습니다.",
        "Add News Article": "뉴스 기사 추가",
        "Attach a credible source, summarize clearly, and keep it civil.": "신뢰할 수 있는 출처를 첨부하고, 명확하게 요약하며, 정중한 표현을 유지해 주세요.",
        "We store title, link, summary & content to compute bias scores.": "편향 점수를 계산하기 위해 제목, 링크, 요약 및 내용을 저장합니다.",
        "Article Title": "기사 제목",
        "Enter the article headline…": "기사 제목을 입력하세요…",
        "Keep it faithful to the original headline.": "원래 제목의 의미를 충실히 반영해 주세요.",
        "Article Link": "기사 링크",
        "https://example.com/news/article": "https://example.com/news/article",
        "We'll try to pull the full text from the URL for you to review and edit.": "URL에서 본문을 가져와 검토하고 수정할 수 있도록 시도합니다.",
        "Extract Content": "본문 추출",
        "Summarize the article in 2–3 sentences…": "기사를 2~3문장으로 요약해 주세요…",
        "Be neutral and concise; avoid personal opinions here.": "중립적이고 간결하게 작성해 주세요. 이곳에는 개인 의견을 넣지 마세요.",
        "News Content": "뉴스 본문",
        "Paste or edit the extracted article text…": "추출된 기사 본문을 붙여넣거나 수정하세요…",
        "Edit for clarity. Don't include unrelated or harmful content.": "더 명확하게 다듬어 주세요. 관련 없거나 유해한 내용은 포함하지 마세요.",
        "Guidelines": "가이드라인",
        "Stay on topic and cite credible sources.": "주제를 벗어나지 말고 신뢰할 수 있는 출처를 인용해 주세요.",
        "No hate speech, harassment, or personal attacks.": "혐오 발언, 괴롭힘, 인신공격은 허용되지 않습니다.",
        "Report misclassified or suspicious sources to an admin.": "잘못 분류되었거나 의심스러운 출처는 관리자에게 신고해 주세요.",
        "After submission, bias and stance will be computed automatically.": "제출 후 편향과 입장이 자동으로 계산됩니다.",
        "Submit News": "뉴스 등록",
        "Please paste a valid link first.": "먼저 올바른 링크를 붙여넣어 주세요.",
        "Extracting…": "추출 중…",
        "Error:": "오류:",
        "Failed to extract content.": "내용을 추출하지 못했습니다.",
        "Request failed. Please check the link or try again later.": "요청에 실패했습니다. 링크를 확인하거나 잠시 후 다시 시도해 주세요.",
        "Bias • Summary • Transparency": "편향 • 요약 • 투명성",
        "See the story behind the story.": "기사 뒤에 숨은 맥락까지 살펴보세요.",
        "FairRead analyzes any article for political lean, explains why, and returns a concise summary you can trust.": "FairRead는 모든 기사의 정치적 성향을 분석하고 그 이유를 설명하며, 신뢰할 수 있는 간결한 요약을 제공합니다.",
        "Analyze an Article": "기사 분석하기",
        "Explore Features": "기능 살펴보기",
        "Private by default • URL · Text · PDF": "기본 비공개 • URL · 텍스트 · PDF",
        "Preview": "미리보기",
        "Bias · Confidence · Key signals": "편향 · 신뢰도 · 핵심 신호",
        "About": "소개",
        "FairRead explained": "FairRead 소개",
        "FairRead is a lightweight tool for evaluating news articles with clarity and speed. Paste a link, text, or PDF and receive an objective read on where the piece leans.": "FairRead는 뉴스 기사를 빠르고 명확하게 평가할 수 있는 가벼운 도구입니다. 링크, 텍스트 또는 PDF를 붙여넣으면 해당 기사 성향에 대한 객관적인 분석을 받아볼 수 있습니다.",
        "Results include a brief rationale so you can see the cues behind the call — not just the label. Your history stays private and helps you understand your own reading patterns over time.": "결과에는 간단한 근거가 함께 제공되어 단순한 라벨이 아니라 판단의 단서를 확인할 수 있습니다. 기록은 기본적으로 비공개로 유지되며, 시간이 지나며 자신의 읽기 패턴을 이해하는 데 도움이 됩니다.",
        "Bias classification with confidence": "신뢰도와 함께 제공되는 편향 분류",
        "Evidence-based rationale (framing, sources, wording)": "근거 기반 설명(프레이밍, 출처, 표현)",
        "Concise, source-aware summary": "출처를 고려한 간결한 요약",
        "Personal analytics with privacy by default": "기본 비공개 개인 분석",
        "Capabilities": "주요 기능",
        "A focused toolkit for reading news clearly": "뉴스를 명확하게 읽기 위한 핵심 도구 모음",
        "Everything you need to judge an article—nothing you don't.": "기사를 판단하는 데 필요한 기능만 담았습니다.",
        "Bias classification with rationale": "근거가 포함된 편향 분류",
        "Left / center / right paired with the specific cues that informed the call (framing, sources, wording).": "좌 / 중 / 우 결과와 함께 판단에 사용된 구체적 단서(프레이밍, 출처, 표현)를 보여줍니다.",
        "Clear, skimmable summaries that preserve context and map claims to evidence.": "맥락을 유지하면서 주장과 근거를 연결해 주는 명확하고 훑어보기 쉬운 요약을 제공합니다.",
        "Learning features": "학습 기능",
        "Study article terms": "기사 용어 학습",
        "Open the Learn tab after analysis to review vocabulary, idioms, and grammar in the article language with English support.": "분석 후 Learn 탭을 열어 기사 언어의 어휘, 관용구, 문법을 영어 설명과 함께 복습하세요.",
        "Learning mode": "학습 모드",
        "Practice terms from your articles and keep them in the article language.": "내 기사에서 나온 용어를 연습하고 기사 언어 그대로 익히세요.",
        "Private reading analytics": "비공개 읽기 분석",
        "See trends in outlets and perspectives over time—stored locally by default.": "매체와 관점의 변화를 לאורך 시간에 따라 확인하세요. 기본적으로 로컬에 저장됩니다.",
        "Flexible inputs": "유연한 입력 방식",
        "Analyze URLs, pasted text, or PDFs. Robust parsing for long-form pieces.": "URL, 붙여넣은 텍스트, PDF를 분석할 수 있으며, 긴 글도 안정적으로 처리합니다.",
        "Quality & controls": "품질 및 제어",
        "Deterministic modes for consistency and clear versioned outputs for sharing.": "일관성을 위한 결정적 모드와 공유하기 쉬운 명확한 버전 출력이 제공됩니다.",
        "Getting Started": "시작하기",
        "How to Use FairRead": "FairRead 사용 방법",
        "Follow three quick steps to analyze any news article with clarity and transparency.": "세 가지 간단한 단계로 어떤 뉴스 기사든 명확하고 투명하게 분석해 보세요.",
        "1. Provide the article": "1. 기사 제공",
        "Enter a link, paste the text, or upload a PDF.": "링크를 입력하거나 텍스트를 붙여넣거나 PDF를 업로드하세요.",
        "2. Let AI analyze": "2. AI 분석 시작",
        "FairRead detects political bias, highlights key signals, and summarizes the piece.": "FairRead가 정치적 편향을 감지하고 핵심 신호를 강조하며 기사를 요약합니다.",
        "3. Review insights": "3. 결과 확인",
        "See the bias label, rationale, and a concise summary you can trust.": "신뢰할 수 있는 편향 라벨, 근거, 간결한 요약을 확인하세요.",
        "Community": "커뮤니티",
        "Discuss, compare, and learn together": "함께 토론하고 비교하며 배워보세요",
        "Join focused debate rooms on live topics, compare evidence, and see how perspectives shift—without sacrificing civility or privacy.": "현재 이슈에 대한 집중 토론방에 참여해 근거를 비교하고 관점의 변화를 살펴보세요. 예의와 개인정보 보호를 해치지 않습니다.",
        "Explore Debate Rooms": "토론방 살펴보기",
        "Topic-Focused Rooms": "주제별 토론방",
        "Join curated rooms on specific policy issues. Keep discussions on track with structured prompts and timeboxed rounds.": "특정 정책 이슈에 맞춘 큐레이션 토론방에 참여하세요. 구조화된 프롬프트와 제한된 라운드로 논의를 주제에 맞게 유지합니다.",
        "Weekly prompts and summaries": "주간 프롬프트 및 요약",
        "Invite-only or public access": "초대 전용 또는 공개 접근",
        "Evidence-Linked Posts": "근거 연결 게시글",
        "Back claims with links or PDFs. FairRead highlights bias signals in cited content so participants can assess sources quickly.": "링크나 PDF로 주장을 뒷받침하세요. FairRead가 인용된 콘텐츠의 편향 신호를 강조해 참가자들이 출처를 빠르게 평가할 수 있도록 돕습니다.",
        "Inline article analysis": "인라인 기사 분석",
        "Quote and counter-quote threads": "인용 및 반박 스레드",
        "Civility & Privacy": "예의와 개인정보 보호",
        "Moderation tools and private rooms reduce noise. Participation history stays local by default; share only what you choose.": "관리 도구와 비공개 방이 불필요한 잡음을 줄여 줍니다. 참여 기록은 기본적으로 로컬에 저장되며, 원하는 내용만 공유할 수 있습니다.",
        "Report & mute controls": "신고 및 음소거 기능",
        "Privacy-first analytics": "개인정보 우선 분석",
        "Weekly Topic": "주간 주제",
        "Each week introduces a new debate prompt with a short neutral brief to frame the discussion.": "매주 새로운 토론 주제가 짧고 중립적인 안내문과 함께 제공되어 논의의 틀을 잡아 줍니다.",
        "Structured Rounds": "구조화된 라운드",
        "Opening statements, evidence posts, and closing remarks keep conversations concise and comparable.": "모두발언, 근거 게시글, 마무리 발언으로 대화를 간결하고 비교 가능하게 유지합니다.",
        "Outcome Snapshot": "결과 요약",
        "See a neutral wrap-up: main claims, strongest evidence cited, and perspective shift over the week.": "한 주 동안의 주요 주장, 가장 강력한 근거, 관점의 변화를 중립적으로 정리해 보여줍니다.",
        "© 2024~2026 FairRead. All Rights Reserved.": "© 2024~2026 FairRead. 모든 권리 보유.",
        "Learn from this article": "이 기사에서 배우기",
        "Learning Term Review": "학습 용어 복습",
        "Review extracted terms by timeframe.": "기간별로 추출된 용어를 복습하세요.",
        "Day": "일",
        "Week": "주",
        "Month": "월",
        "No learning terms yet": "아직 학습 용어가 없습니다",
        "Terms from your learned articles will appear here.": "학습한 기사의 용어가 여기에 표시됩니다.",
        "Week of": "해당 주",
        "All Terms": "전체 용어",
        "Learned": "학습 완료",
        "Not learned": "미학습",
        "Learning Terms": "학습 용어",
        "Click any term to see details": "용어를 클릭하여 세부 정보 보기",
        "Vocabulary": "어휘",
        "Idiom": "관용구",
        "Grammar": "문법 패턴",
        "Beginner": "초급",
        "Intermediate": "중급",
        "Advanced": "고급",
        "Definition": "정의",
        "Example": "예",
        "Part of Speech": "품사",
        "Difficulty": "난이도",
        "Grammar Note": "문법 설명",
        "Your language": "사용자 언어",
        "Article language": "기사 언어",
        "Total Terms": "총 용어 수",
        "Back to Analysis": "분석으로 돌아가기",
        "Generating learning terms...": "학습 용어 생성 중...",
        "Extracting learning terms...": "학습 용어 추출 중...",
        "This usually takes 10-30 seconds.": "보통 10~30초 정도 걸립니다.",
        "Still working...": "아직 처리 중입니다...",
        "If this takes too long, please refresh.": "너무 오래 걸리면 새로고침해 주세요.",
        "Extraction is taking longer than expected.": "추출이 예상보다 오래 걸리고 있습니다.",
        "Failed to generate learning terms.": "학습 용어 생성에 실패했습니다.",
    },
}
def translate_bias_label(label, language='en'):

    """Translate bias label (Left/Center/Right) to selected language."""

    return BIAS_LABELS.get(language, {}).get(label, label)



def translate_ui(key, language='en'):

    """Translate UI text to selected language."""

    return UI_LABELS.get(language, {}).get(key, key)



@app.context_processor

def inject_globals():

    """Make translation functions available in all templates."""

    return {

        'translate_bias_label': translate_bias_label,

        'translate_ui': translate_ui,

        'current_language': session.get('language', 'en'),
        'is_login': 'username' in session,
        'is_admin': is_admin_user()

    }



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

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    if request.method == "POST":

        topic = request.form.get("topic")

        now_iso = now_kst().isoformat()
        _supabase_insert_resilient("debates", {
            "topic": topic,
            "created_at": now_iso,
            "is_closed": False,
            "date": now_kst().date().isoformat(),
            "isClosed": False
        })

        return redirect(url_for('create_debate'))

    debates_res = (
        supabase.table("debates")
        .select("*")
        .order("id", desc=True)
        .execute()
    )
    open_debates = []
    closed_debates = []
    for row in (debates_res.data or []):
        debate_tuple = (
            _pick_row_value(row, "id"),
            _pick_row_value(row, "topic", "title", default=""),
            _display_date(_pick_row_value(row, "created_at", "date"))
        )
        if _coerce_bool(_pick_row_value(row, "is_closed", "isClosed")):
            closed_debates.append(debate_tuple)
        else:
            open_debates.append(debate_tuple)

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

    if supabase is None:
        abort(500, description="Supabase is not configured.")
    supabase.table("debates").delete().eq("id", debate_id).execute()

    return redirect(url_for('create_debate'))



@app.route('/delete_post/<int:post_id>/<int:debate_id>', methods=['POST'])

def delete_post(post_id, debate_id):

    username = session.get('username')

    if not username:

        return redirect(url_for('login'))



    if supabase is None:
        abort(500, description="Supabase is not configured.")

    post_res = (
        supabase.table("posts")
        .select("id,username")
        .eq("id", post_id)
        .limit(1)
        .execute()
    )
    row = (post_res.data or [None])[0]
    if not row:
        return redirect(url_for('debate_detail', debate_id=debate_id))

    author = row.get("username")



    is_admin = (username == 'testtest')

    if not (is_admin or username == author):

        abort(403)



    supabase.table("post_comments").delete().eq("post_id", post_id).execute()
    supabase.table("post_likes").delete().eq("post_id", post_id).execute()
    supabase.table("posts").delete().eq("id", post_id).execute()



    return redirect(url_for('debate_detail', debate_id=debate_id))



@app.route('/delete_news/<int:news_id>/<int:debate_id>', methods=['POST'])

def delete_news(news_id, debate_id):

    username = session.get('username')

    if not username:

        return redirect(url_for('login'))

    if username != 'testtest':

        abort(403)



    if supabase is None:
        abort(500, description="Supabase is not configured.")
    supabase.table("news_votes").delete().eq("news_id", news_id).execute()
    supabase.table("news").delete().eq("id", news_id).execute()



    return redirect(url_for('debate_detail', debate_id=debate_id))



@app.route('/close_debate/<int:debate_id>', methods=['POST'])

def close_debate(debate_id):

    if supabase is None:
        abort(500, description="Supabase is not configured.")
    try:
        supabase.table("debates").update({"is_closed": True}).eq("id", debate_id).execute()
    except APIError as e:
        missing_col = _extract_missing_column_name(e)
        if missing_col == "is_closed":
            supabase.table("debates").update({"isClosed": True}).eq("id", debate_id).execute()
        else:
            raise

    return redirect(url_for('create_debate'))



@app.route('/create_news/<int:debate_id>', methods=['GET','POST'])

def create_news(debate_id):

    is_login = 'username' in session
    if supabase is None:
        abort(500, description="Supabase is not configured.")

    debate_res = (
        supabase.table("debates")
        .select("*")
        .eq("id", debate_id)
        .limit(1)
        .execute()
    )
    debate_row = (debate_res.data or [None])[0]
    debate = None
    if debate_row:
        debate = (
            _pick_row_value(debate_row, "id"),
            _pick_row_value(debate_row, "topic", "title", default=""),
            _display_date(_pick_row_value(debate_row, "created_at", "date")),
            _coerce_bool(_pick_row_value(debate_row, "is_closed", "isClosed"))
        )
    if not debate:
        return redirect(url_for('create_debate'))



    if request.method == "POST":

        summary = request.form.get('summary')

        link = request.form.get('link')

        title = request.form.get('title')

        content = request.form.get('content')


        language = session.get('language', 'en')
        classification, percentages, bias_scores = get_bias_classification(content, language)
        left, center, right = bias_scores



        _supabase_insert_resilient("news", {
            "debate_id": debate_id,
            "title": title,
            "link": link,
            "summary": summary,
            "classification": classification,
            "left_score": left,
            "center_score": center,
            "right_score": right,
            "left": left,
            "center": center,
            "right": right
        })

        return redirect(url_for('debate_detail', debate_id=debate_id))



    return render_template('create_news.html',

                           is_login=is_login,

                           is_admin=is_admin_user(),

                           debate=debate)



@app.route('/create_post/<int:debate_id>', methods=['GET','POST'])

def create_post(debate_id):

    is_login = 'username' in session
    if supabase is None:
        abort(500, description="Supabase is not configured.")

    debate_res = (
        supabase.table("debates")
        .select("*")
        .eq("id", debate_id)
        .limit(1)
        .execute()
    )
    debate_row = (debate_res.data or [None])[0]
    debate = None
    if debate_row:
        debate = (
            _pick_row_value(debate_row, "id"),
            _pick_row_value(debate_row, "topic", "title", default=""),
            _display_date(_pick_row_value(debate_row, "created_at", "date")),
            _coerce_bool(_pick_row_value(debate_row, "is_closed", "isClosed"))
        )
    if not debate:
        return redirect(url_for('create_debate'))



    if request.method == "POST":

        content = request.form.get('content')

        timestamp = now_kst().isoformat()
        _supabase_insert_resilient("posts", {
            "debate_id": debate_id,
            "username": session['username'],
            "content": content,
            "created_at": timestamp,
            "timestamp": timestamp
        })

        return redirect(url_for('debate_detail', debate_id=debate_id))



    return render_template('create_post.html',

                           is_login=is_login,

                           is_admin=is_admin_user(),

                           debate=debate)



@app.route('/debate/<int:debate_id>')

def debate_detail(debate_id):

    user = session.get("username")

    is_login = 'username' in session

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    debate_res = (
        supabase.table("debates")
        .select("*")
        .eq("id", debate_id)
        .limit(1)
        .execute()
    )
    debate_row = (debate_res.data or [None])[0]
    debate = None
    if debate_row:
        debate = (
            _pick_row_value(debate_row, "id"),
            _pick_row_value(debate_row, "topic", "title", default=""),
            _display_date(_pick_row_value(debate_row, "created_at", "date")),
            _coerce_bool(_pick_row_value(debate_row, "is_closed", "isClosed"))
        )
    if not debate:
        return redirect(url_for('create_debate'))

    posts_res = (
        supabase.table("posts")
        .select("*")
        .eq("debate_id", debate_id)
        .order("id", desc=True)
        .execute()
    )
    posts_rows = posts_res.data or []
    posts = []
    for row in posts_rows:
        posts.append((
            _pick_row_value(row, "id"),
            _pick_row_value(row, "username", default=""),
            _pick_row_value(row, "content", default=""),
            _display_date(_pick_row_value(row, "created_at", "timestamp"))
        ))

    post_ids = [p[0] for p in posts if p[0] is not None]
    likes_dict = {}
    if post_ids:
        likes_res = (
            supabase.table("post_likes")
            .select("post_id")
            .in_("post_id", post_ids)
            .execute()
        )
        for row in (likes_res.data or []):
            pid = row.get("post_id")
            likes_dict[pid] = likes_dict.get(pid, 0) + 1

    comments_dict = {}
    if post_ids:
        comments_res = (
            supabase.table("post_comments")
            .select("*")
            .in_("post_id", post_ids)
            .order("id")
            .execute()
        )
        for row in (comments_res.data or []):
            pid = row.get("post_id")
            comments_dict.setdefault(pid, []).append((
                _pick_row_value(row, "username", default=""),
                _pick_row_value(row, "comment", default=""),
                _display_date(_pick_row_value(row, "created_at", "timestamp"))
            ))

    news_res = (
        supabase.table("news")
        .select("*")
        .eq("debate_id", debate_id)
        .order("id", desc=True)
        .execute()
    )
    news_rows = news_res.data or []
    news_ids = [n.get("id") for n in news_rows if n.get("id") is not None]
    voted_news_ids = set()
    if user and news_ids:
        votes_res = (
            supabase.table("news_votes")
            .select("news_id")
            .eq("username", user)
            .in_("news_id", news_ids)
            .execute()
        )
        voted_news_ids = {row.get("news_id") for row in (votes_res.data or [])}

    news = []
    for row in news_rows:
        news_id = _pick_row_value(row, "id")
        left = _pick_row_value(row, "left_score", "left", default=0) or 0
        center = _pick_row_value(row, "center_score", "center", default=0) or 0
        right = _pick_row_value(row, "right_score", "right", default=0) or 0
        news.append((
            news_id,
            _pick_row_value(row, "title", default=""),
            _pick_row_value(row, "link", default=""),
            _pick_row_value(row, "summary", default=""),
            _pick_row_value(row, "classification", default=""),
            left,
            center,
            right,
            news_id in voted_news_ids
        ))



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

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    like_res = (
        supabase.table("post_likes")
        .select("id")
        .eq("post_id", post_id)
        .eq("username", username)
        .limit(1)
        .execute()
    )
    existing_like = (like_res.data or [None])[0]

    if not existing_like:
        ts = now_kst().isoformat()
        _supabase_insert_resilient("post_likes", {
            "post_id": post_id,
            "username": username,
            "created_at": ts,
            "timestamp": ts
        })
    else:
        supabase.table("post_likes").delete().eq("id", existing_like.get("id")).execute()

    post_res = (
        supabase.table("posts")
        .select("debate_id")
        .eq("id", post_id)
        .limit(1)
        .execute()
    )
    post_row = (post_res.data or [None])[0]
    if not post_row:
        return redirect(url_for('create_debate'))
    debate_id = post_row.get("debate_id") if post_row else None

    return redirect(url_for('debate_detail', debate_id=debate_id))



@app.route('/comment_post/<int:post_id>', methods=['POST'])

def comment_post(post_id):

    username = session.get('username')

    if not username:

        return redirect(url_for('login'))

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    post_res = (
        supabase.table("posts")
        .select("debate_id")
        .eq("id", post_id)
        .limit(1)
        .execute()
    )
    post_row = (post_res.data or [None])[0]
    if not post_row:
        return redirect(url_for('create_debate'))
    debate_id = post_row.get("debate_id") if post_row else None

    comment = request.form.get('comment')

    if comment:
        ts = now_kst().isoformat()
        _supabase_insert_resilient("post_comments", {
            "post_id": post_id,
            "username": username,
            "comment": comment,
            "created_at": ts,
            "timestamp": ts
        })

    return redirect(url_for('debate_detail', debate_id=debate_id))



@app.route('/vote_news/<int:news_id>/<int:debate_id>', methods=["POST"])

def vote_news(news_id, debate_id):

    username = session.get("username")

    if not username:

        return redirect(url_for('login'))



    if supabase is None:
        abort(500, description="Supabase is not configured.")

    vote_res = (
        supabase.table("news_votes")
        .select("id")
        .eq("username", username)
        .eq("news_id", news_id)
        .limit(1)
        .execute()
    )
    if not (vote_res.data or []):
        now = now_kst().isoformat()
        _supabase_insert_resilient("news_votes", {
            "username": username,
            "news_id": news_id,
            "voted_at": now,
            "vote_value": request.form.get("vote")
        })



    return redirect(url_for('debate_detail', debate_id=debate_id))



@app.route('/chatbot')

def chatbot():

    is_login = 'username' in session

    if not is_login:

        return redirect(url_for('login'))

    return render_template('chatbot.html', is_login=is_login, is_admin=is_admin_user())


@app.route('/wordle')
def wordle_page():
    is_login = 'username' in session
    if not is_login:
        return redirect(url_for('login'))
    return render_template('wordle.html', is_login=is_login, is_admin=is_admin_user())



@app.route('/profile')

def profile():

    is_login = 'username' in session

    if not is_login:

        return redirect(url_for('login'))



    initial_term_range = request.args.get('term_range', 'week')
    if initial_term_range not in ['day', 'week', 'month', 'all']:
        initial_term_range = 'week'

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    recent_res = (
        supabase.table("chatlog")
        .select("id,created_at,question,bias_class,bias_percentage,summary,reason,is_url")
        .eq("username", session["username"])
        .order("created_at", desc=True)
        .limit(5)
        .execute()
    )
    recent_classification = [
        (
            row.get("id"),
            _display_date(row.get("created_at")),
            row.get("question"),
            row.get("bias_class"),
            row.get("bias_percentage"),
            row.get("summary"),
            row.get("reason"),
            row.get("is_url"),
        )
        for row in (recent_res.data or [])
    ]

    email_res = (
        supabase.table("users")
        .select("email")
        .eq("username", session["username"])
        .limit(1)
        .execute()
    )
    email_row = (email_res.data or [None])[0]
    email = email_row.get("email") if email_row and email_row.get("email") else ""

    rows_res = (
        supabase.table("chatlog")
        .select("id,created_at,question,bias_class,bias_percentage,summary,reason,is_url")
        .eq("username", session["username"])
        .execute()
    )
    rows = [
        (
            row.get("id"),
            _display_date(row.get("created_at")),
            row.get("question"),
            row.get("bias_class"),
            row.get("bias_percentage"),
            row.get("summary"),
            row.get("reason"),
            row.get("is_url"),
        )
        for row in (rows_res.data or [])
    ]

    chatlog_by_id = {row[0]: row for row in rows}
    ann_res = (
        supabase.table("learning_annotations")
        .select("article_id,term,term_type,definition,english_meaning,target_language,difficulty,id")
        .order("id", desc=True)
        .execute()
    )
    term_rows = []
    for ann in (ann_res.data or []):
        article_id = ann.get("article_id")
        chat_row = chatlog_by_id.get(article_id)
        if not chat_row:
            continue
        term_rows.append((
            ann.get("term"),
            ann.get("term_type"),
            ann.get("definition"),
            ann.get("english_meaning"),
            ann.get("target_language"),
            ann.get("difficulty"),
            chat_row[1],
        ))



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

        scores = safe_parse_scores(classification[4])
        bias_scores.append(scores if scores else [0, 0, 0])

    def parse_saved_datetime(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            pass
        for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    current_language = session.get('language', 'en')

    def build_term_groups(range_key):
        term_groups_map = defaultdict(list)
        term_group_sort = {}

        for term, term_type, definition, english_meaning, target_language, difficulty, saved_date in term_rows:
            dt = parse_saved_datetime(saved_date)

            if range_key == 'day':
                if dt:
                    group_key = dt.strftime('%Y-%m-%d')
                    group_sort = dt.replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    group_key = 'unknown'
                    group_sort = datetime.min
            elif range_key == 'week':
                if dt:
                    week_start = dt - timedelta(days=dt.weekday())
                    group_key = week_start.strftime('%Y-%m-%d')
                    group_sort = week_start
                else:
                    group_key = 'unknown'
                    group_sort = datetime.min
            elif range_key == 'month':
                if dt:
                    group_key = dt.strftime('%Y-%m')
                    group_sort = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                else:
                    group_key = 'unknown'
                    group_sort = datetime.min
            else:
                group_key = 'all'
                group_sort = datetime.max

            definition_en = english_meaning or definition or ''
            definition_target = definition or ''
            definition_target_lang = target_language or current_language
            display_definition = definition_target
            if current_language == 'en':
                display_definition = definition_en
            elif target_language and target_language != current_language and english_meaning:
                display_definition = definition_en

            term_groups_map[group_key].append({
                'term': term,
                'type': term_type,
                'definition': display_definition,
                'definition_en': definition_en,
                'definition_target': definition_target,
                'definition_target_lang': definition_target_lang,
                'difficulty': difficulty or '',
                'date': saved_date or ''
            })
            term_group_sort[group_key] = max(term_group_sort.get(group_key, datetime.min), group_sort)

        sorted_groups = sorted(term_groups_map.keys(), key=lambda k: term_group_sort.get(k, datetime.min), reverse=True)
        output = []
        for group_key in sorted_groups:
            if range_key == 'all':
                group_label = translate_ui('All Terms', session.get('language', 'en'))
            elif group_key == 'unknown':
                group_label = 'Unknown'
            elif range_key == 'week':
                first_item_date = term_groups_map[group_key][0]['date']
                dt = parse_saved_datetime(first_item_date)
                if dt:
                    week_start = dt - timedelta(days=dt.weekday())
                    week_end = week_start + timedelta(days=6)
                    group_label = f"{translate_ui('Week of', session.get('language', 'en'))} {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}"
                else:
                    group_label = 'Unknown'
            else:
                group_label = group_key

            output.append({'label': group_label, 'items': term_groups_map[group_key]})
        return output

    term_groups_by_range = {
        'day': build_term_groups('day'),
        'week': build_term_groups('week'),
        'month': build_term_groups('month'),
        'all': build_term_groups('all')
    }
    term_total_count = len(term_rows)



    return render_template('profile.html',

                           bias_scores=bias_scores,

                           left_avg=left_avg, center_avg=center_avg, right_avg=right_avg,

                           total_articles=total_articles,

                           username=session["username"],

                           is_login=is_login,

                           is_admin=is_admin_user(),

                           email=email,

                           recent_classification=recent_classification,
                           term_groups_by_range=term_groups_by_range,
                           term_total_count=term_total_count,
                           initial_term_range=initial_term_range)



@app.route('/statistics')

def statistics():

    if not is_admin_user():

        return redirect(url_for('index'))

    is_login = 'username' in session



    current_date = now_kst()
    current_date_cmp = current_date.replace(tzinfo=None) if current_date.tzinfo else current_date

    seven_days_ago = current_date - timedelta(days=7)
    seven_days_ago_cmp = current_date_cmp - timedelta(days=7)
    if supabase is None:
        abort(500, description="Supabase is not configured.")

    def parse_dt(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        text = str(value).strip()
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(text, fmt)
                except ValueError:
                    continue
        return None

    chatlog_res = (
        supabase.table("chatlog")
        .select("created_at,keywords,bias_percentage")
        .execute()
    )
    chatlog_rows = chatlog_res.data or []

    users_res = (
        supabase.table("users")
        .select("recent_login")
        .execute()
    )
    user_rows = users_res.data or []

    date_counts = defaultdict(int)
    month_counts = defaultdict(int)
    for row in chatlog_rows:
        dt = parse_dt(row.get("created_at"))
        if not dt:
            continue
        day_key = dt.strftime('%Y-%m-%d')
        month_key = dt.strftime('%Y-%m')
        month_counts[month_key] += 1
        if seven_days_ago.date() <= dt.date() <= current_date.date():
            date_counts[day_key] += 1

    result = sorted(date_counts.items(), key=lambda x: x[0])
    monthly_result = sorted(month_counts.items(), key=lambda x: x[0])

    total_users = len(user_rows)
    thirty_days_ago = current_date - timedelta(days=30)
    active_users = 0
    for row in user_rows:
        dt = parse_dt(row.get("recent_login"))
        if dt:
            dt_cmp = dt.replace(tzinfo=None) if dt.tzinfo else dt
            if dt_cmp >= thirty_days_ago.replace(tzinfo=None) if thirty_days_ago.tzinfo else thirty_days_ago:
                active_users += 1

    total_news = len(chatlog_rows)
    recent_news = 0
    for row in chatlog_rows:
        dt = parse_dt(row.get("created_at"))
        if dt:
            dt_cmp = dt.replace(tzinfo=None) if dt.tzinfo else dt
            threshold = thirty_days_ago.replace(tzinfo=None) if thirty_days_ago.tzinfo else thirty_days_ago
            if dt_cmp >= threshold:
                recent_news += 1

    rows = [(row.get("keywords"),) for row in chatlog_rows]

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

    bias_rows = [(row.get("bias_percentage"), row.get("keywords")) for row in chatlog_rows]



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



    session_counts_map = defaultdict(int)
    for row in user_rows:
        dt = parse_dt(row.get("recent_login"))
        if dt:
            dt_cmp = dt.replace(tzinfo=None) if dt.tzinfo else dt
            if seven_days_ago_cmp.date() <= dt_cmp.date() <= current_date_cmp.date():
                session_counts_map[dt_cmp.strftime('%Y-%m-%d')] += 1
    session_result = sorted(session_counts_map.items(), key=lambda x: x[0])

    session_dates = [row[0] for row in session_result]

    session_counts = [row[1] for row in session_result]



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



@app.route('/learn_status/<int:article_id>')
def learn_status(article_id):
    """Check if learning annotations are ready. Returns JSON with ready status."""
    is_login = 'username' in session
    if not is_login:
        return jsonify({'ready': False}), 401

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    result = (
        supabase.table("learning_annotations")
        .select("id", count="exact")
        .eq("article_id", article_id)
        .limit(1)
        .execute()
    )

    return jsonify({'ready': (result.count or 0) > 0})

@app.route('/learn')
def learn_home():
    is_login = 'username' in session
    if not is_login:
        return redirect(url_for('login'))

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    articles_res = (
        supabase.table("chatlog")
        .select("id,created_at,question,bias_class,summary")
        .eq("username", session['username'])
        .order("created_at", desc=True)
        .limit(20)
        .execute()
    )
    articles = articles_res.data or []
    article_ids = [a.get("id") for a in articles if a.get("id") is not None]

    learned_ids = set()
    if article_ids:
        learned_res = (
            supabase.table("learning_annotations")
            .select("article_id")
            .in_("article_id", article_ids)
            .execute()
        )
        learned_ids = {row.get("article_id") for row in (learned_res.data or [])}

    recent_articles = []
    for a in articles:
        recent_articles.append((
            a.get("id"),
            a.get("created_at"),
            a.get("question") or "",
            a.get("bias_class") or "",
            a.get("summary") or "",
            a.get("id") in learned_ids
        ))

    return render_template(
        'learn_home.html',
        recent_articles=recent_articles,
        is_login=is_login,
        is_admin=is_admin_user()
    )

@app.route('/learn/<int:article_id>')
def learn_from_article(article_id):
    is_login = 'username' in session
    if not is_login:
        return redirect(url_for('login'))

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    article_res = (
        supabase.table("chatlog")
        .select("id,question,summary,created_at,bias_class,is_url")
        .eq("id", article_id)
        .eq("username", session['username'])
        .limit(1)
        .execute()
    )
    article = (article_res.data or [None])[0]

    if not article:
        return redirect(url_for('chatbot'))

    article_id_db = article.get("id")
    article_url = article.get("question")
    from chatbot import detect_article_language
    detected_article_language = detect_article_language(article_url or "")

    # Fetch or generate learning annotations
    ann_res = (
        supabase.table("learning_annotations")
        .select("id,term,term_type,definition,english_meaning,part_of_speech,example_sentence,difficulty,grammar_note,article_language,target_language")
        .eq("article_id", article_id_db)
        .eq("target_language", session.get('language', 'en'))
        .order("term_type")
        .order("difficulty")
        .execute()
    )
    annotations = ann_res.data or []
    allow_any_annotations = True
    if annotations:
        stored_languages = {(ann.get("article_language") or ann.get("target_language") or 'en') for ann in annotations}
        if stored_languages != {detected_article_language}:
            (
                supabase.table("learning_annotations")
                .delete()
                .eq("article_id", article_id_db)
                .execute()
            )
            annotations = []
            allow_any_annotations = False

    # If no annotations for current UI language, reuse any existing annotations for this article.
    # Do not auto-extract here (prevents blocking page load).
    if not annotations and allow_any_annotations:
        ann_any_res = (
            supabase.table("learning_annotations")
            .select("id,term,term_type,definition,english_meaning,part_of_speech,example_sentence,difficulty,grammar_note,article_language,target_language")
            .eq("article_id", article_id_db)
            .order("term_type")
            .order("difficulty")
            .execute()
        )
        annotations = ann_any_res.data or []
    
    # Format annotations for template
    formatted_annotations = []
    for ann in annotations:
        article_lang = ann.get("article_language") or ann.get("target_language") or session.get('language', 'en')
        formatted_annotations.append({
            'id': ann.get("id"),
            'term': ann.get("term"),
            'type': ann.get("term_type"),
            'definition': ann.get("definition"),
            'english_meaning': ann.get("english_meaning"),
            'part_of_speech': ann.get("part_of_speech"),
            'example_sentence': ann.get("example_sentence"),
            'difficulty': ann.get("difficulty"),
            'grammar_note': ann.get("grammar_note"),
            'article_language': article_lang
        })
    
    return render_template('learn_article.html',
                          article_id=article_id,
                          annotations=formatted_annotations,
                          current_language=session.get('language', 'en'),
                          article_language=detected_article_language)

@app.route('/learn_extract/<int:article_id>', methods=['POST'])
def learn_extract(article_id):
    is_login = 'username' in session
    if not is_login:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    article_res = (
        supabase.table("chatlog")
        .select("id,question")
        .eq("id", article_id)
        .eq("username", session['username'])
        .limit(1)
        .execute()
    )
    article = (article_res.data or [None])[0]
    if not article:
        return jsonify({'ok': False, 'error': 'not_found'}), 404

    article_id_db = article.get("id")
    article_text = article.get("question") or ""
    article_language = detect_article_language(article_text)

    # Never re-extract if already learned once for this article
    existing_res = (
        supabase.table("learning_annotations")
        .select("id,article_language,target_language", count="exact")
        .eq("article_id", article_id_db)
        .execute()
    )
    existing_count = existing_res.count or 0
    if existing_count > 0:
        existing_languages = {
            (row.get("article_language") or row.get("target_language") or 'en')
            for row in (existing_res.data or [])
        }
        if existing_languages == {article_language}:
            return jsonify({'ok': True, 'status': 'already_learned'})
        (
            supabase.table("learning_annotations")
            .delete()
            .eq("article_id", article_id_db)
            .execute()
        )
 
    from chatbot import extract_learning_points
    ui_language = session.get('language', 'en')
    learning_points = extract_learning_points(article_text, article_language, ui_language)

    if not learning_points:
        return jsonify({'ok': False, 'error': 'extract_failed'}), 502

    rows = []
    for point in learning_points:
        rows.append({
            "article_id": article_id_db,
            "user_id": None,
            "target_language": ui_language,
            "term": point['term'],
            "term_type": point['type'],
            "definition": point['definition'],
            "english_meaning": point['english_meaning'],
            "example_sentence": point['example_sentence'],
            "difficulty": point['difficulty'],
            "part_of_speech": point['part_of_speech'],
            "grammar_note": point['grammar_note'],
            "article_language": article_language
        })

    supabase.table("learning_annotations").insert(rows).execute()

    return jsonify({'ok': True, 'status': 'extracted'})

@app.route('/translate_example', methods=['POST'])
def translate_example():
    is_login = 'username' in session
    if not is_login:
        return jsonify({'ok': False, 'error': 'unauthorized'}), 401

    data = request.get_json() or {}
    text = (data.get('text') or '').strip()
    source_language = (data.get('source_language') or 'en').strip().lower()
    target_language = (data.get('target_language') or source_language).strip().lower()
    language_names = {
        'en': 'English',
        'es': 'Spanish',
        'zh': 'Chinese',
        'ko': 'Korean'
    }
    if source_language not in language_names:
        source_language = 'en'
    if target_language not in language_names:
        target_language = source_language
    if not text:
        return jsonify({'ok': False, 'error': 'empty_text'}), 400

    if source_language == 'en' and target_language == 'en':
        return jsonify({'ok': True, 'en': text, 'target': text})

    prompt = f"""
Translate this text from {language_names[source_language]} into English and {language_names[target_language]}.
Preserve names and factual meaning.
Return ONLY valid JSON:
{{
  "en": "English translation",
  "target": "{language_names[target_language]} translation"
}}

Text:
{text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        payload = response.choices[0].message.content.strip()
        parsed = json.loads(payload)
        en_text = (parsed.get('en') or '').strip()
        target_text = (parsed.get('target') or '').strip()
        if not en_text:
            en_text = text
        if not target_text:
            target_text = text
        return jsonify({'ok': True, 'en': en_text, 'target': target_text})
    except Exception:
        return jsonify({'ok': True, 'en': text, 'target': text})

@app.route('/logout')
def logout():

    session.clear()

    return redirect(url_for('index'))



@app.route('/set_language', methods=['POST'])

def set_language():

    data = request.get_json()

    lang = data.get('language', 'en')

    if lang in ['en', 'es', 'zh', 'ko']:

        session['language'] = lang

    return jsonify({'success': True})


@app.route('/set_tz', methods=['POST'])
def set_tz():
    data = request.get_json() or {}
    tz = (data.get('tz') or '').strip()
    offset_min = data.get('offset_min')
    if tz:
        session['tz'] = tz
    if isinstance(offset_min, int):
        session['tz_offset_min'] = offset_min
    return jsonify({'success': True})



@app.route('/register', methods=["GET", "POST"])

def register():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        email = request.form["email"]

        gender = request.form["gender"]

        age = request.form["age"]

        if supabase is None:
            abort(500, description="Supabase is not configured.")

        existing_user = (
            supabase.table("users")
            .select("username")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        if existing_user.data:
            flash('username already exists')
            return render_template('signup.html')

        payload = {
            "username": username,
            "password": password,
            "email": email,
            "gender": gender,
            "age": age,
        }
        while True:
            try:
                supabase.table("users").insert(payload).execute()
                return redirect(url_for('register', registered=1))
            except APIError as e:
                missing_col = _extract_missing_column_name(e)
                if missing_col and missing_col in payload:
                    payload.pop(missing_col, None)
                    continue
                raise

    registered = request.args.get('registered') == '1'

    return render_template('signup.html', registered=registered)



@app.route('/login', methods=["GET", "POST"])

def login():

    if request.method == "POST":

        username = request.form["username"]

        password = request.form["password"]

        if supabase is None:
            abort(500, description="Supabase is not configured.")

        user_result = (
            supabase.table("users")
            .select("password")
            .eq("username", username)
            .limit(1)
            .execute()
        )
        if not user_result.data:
            flash('Username or password is wrong')
            return render_template('login.html')

        password_db = user_result.data[0]["password"]

        if password == password_db:

            session["username"] = username

            current_time = now_kst().strftime('%Y-%m-%d %H:%M:%S')

            try:
                (
                    supabase.table("users")
                    .update({"recent_login": current_time})
                    .eq("username", username)
                    .execute()
                )
            except APIError as e:
                missing_col = _extract_missing_column_name(e)
                if missing_col != "recent_login":
                    raise

            return redirect(url_for('index'))

        flash('username or password is wrong')

        return render_template('login.html')

    return render_template('login.html')



@app.route('/upload_pdf', methods=["POST"])

def read_file():
    username = current_user()
    if not username:
        return jsonify({"error": "Please log in first."}), 401

    if "pdf_file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400
 
    file = request.files["pdf_file"]

    filename = secure_filename(file.filename)

    if filename.endswith('.pdf'):

        text = read_pdf(file)

    else:

        text = read_docs(file)



    language = session.get('language', 'en')

    bias_class, bias_score, score_lst = get_bias_classification(text, language)
    reason = reason_news(text, bias_class, language)

    summary = summarize_news(text, language)

    keywords = get_keywords(text, language)



    if supabase is None:
        abort(500, description="Supabase is not configured.")

    current_date = now_kst().isoformat()
    _insert_chatlog_resilient({
        "username": username,
        "created_at": current_date,
        "question": text,
        "bias_class": bias_class,
        "bias_percentage": str(bias_score),
        "summary": summary,
        "reason": reason,
        "keywords": keywords,
        "is_url": False
    })



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
    username = current_user()
    if not username:
        return jsonify({"error": "Please log in first."}), 401

    data = request.get_json(silent=True) or {}
    text = str(data.get("message", "")).strip()
    if not text:
        return jsonify({"error": "Message is required."}), 400

    # Check if input is a URL
    is_url = text.lower().startswith(('http://', 'https://', 'www.'))

    if is_url:
        # Fetch article from URL
        from chatbot import fetch_article_from_url
        fetched_text, fetch_error = fetch_article_from_url(text)
        
        if fetch_error:
            return jsonify({
                "error": fetch_error,
                "bias_class": None,
                "left_score": 0,
                "center_score": 0,
                "right_score": 0,
                "keywords": None,
                "reason": None,
                "summary": None
            }), 400
        
        text = fetched_text

    language = session.get('language', 'en')
    bias_class, bias_score, score_lst = get_bias_classification(text, language)
    reason = reason_news(text, bias_class, language)
    summary = summarize_news(text, language)
    keywords = get_keywords(text, language)

    if supabase is None:
        abort(500, description="Supabase is not configured.")

    current_date = now_kst().isoformat()
    insert_res = _insert_chatlog_resilient({
        "username": username,
        "created_at": current_date,
        "question": text,
        "bias_class": bias_class,
        "bias_percentage": str(bias_score),
        "summary": summary,
        "reason": reason,
        "keywords": keywords,
        "is_url": bool(is_url)
    })
    inserted = (insert_res.data or [None])[0]
    article_id = inserted.get("id") if inserted else None
    if article_id is None:
        latest_res = (
            supabase.table("chatlog")
            .select("id")
            .eq("username", username)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        latest = (latest_res.data or [None])[0]
        article_id = latest.get("id") if latest else None

    return jsonify({
        "bias_class": bias_class,
        "left_score": score_lst[0],
        "center_score": score_lst[1],
        "right_score": score_lst[2],
        "keywords": keywords,
        "reason": reason,
        "summary": summary,
        "article_id": article_id,
        "is_url": is_url
    })


if __name__ == "__main__":

    app.run(debug=True, port=8080)
