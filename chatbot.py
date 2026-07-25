from openai import OpenAI
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup
from collections import Counter
# import torch # popular library for deep learning
# from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline # AutoTokenizer --> text preprocessing
from docx import Document
import pdfplumber
import yake
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key=api_key)

# Language code to full name mapping for GPT prompts
LANGUAGE_NAMES = {
    'en': 'English',
    'es': 'Spanish',
    'zh': 'Chinese',
    'ko': 'Korean'
}

def get_language_instruction(language_code='en'):
    """Returns language instruction for GPT prompts. Always respond in the selected language."""
    lang_name = LANGUAGE_NAMES.get(language_code, 'English')
    return f"Respond entirely in {lang_name}."

# tokenizer = AutoTokenizer.from_pretrained("bucketresearch/politicalBiasBERT")
# model = AutoModelForSequenceClassification.from_pretrained("bucketresearch/politicalBiasBERT")
#
# summarizer = pipeline('summarization', model="facebook/bart-large-cnn")

# function for summarizing text
def summarize_text(text, language_code="en"):
    summary = summarizer(text, max_length=max_length, min_length=min_length, do_sample=False)
    return summary[0]['summary_text']

# Function to classify bias and return bias class (left,right,center) and score.
# def get_bias_classification(text):
#     inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
#     # performs the classifcation to get model otput
#     with torch.no_grad():
#         outputs = model(**inputs) # feed the preprocssed inputs into the pre-trained model
#
#     # torch.nn.functional.softmax --> converts the raw data into probailites ex) left: 10%, center: 60%, right: 30%
#     predictions = torch.nn.functional.softmax(outputs.logits, dim=1)
#     bias_class = torch.argmax(predictions, dim=1).item() # get the predicted class(left,right,center)
#     class_labels = ["Left", "Center", "Right"]
#     bias_score = predictions[0].tolist()
#
#     if (bias_class == 0 or bias_class == 2) and bias_score[bias_class] > 0.5:
#         return class_labels[bias_class], bias_score
#     else:
#         return "Center", bias_score

def is_news(text):
    return


def get_bias_classification(text, language='en'):
    classification_prompt = (
        "Classify the following news whether it is bias toward certain wing as 'Left', 'Center', or 'Right'. "
        "Provide the classification and the probability for each class as percentages. "
        "Example format: {'Left': 30%, 'Center': 50%, 'Right': 20%}\n\n"
        f"Text: {text}\n\n"
        "Output:"
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0
    )

    result = response.choices[0].message.content.strip()

    result = result.replace("%","")
    percentages = eval(result)  # Parse string output as a Python dictionary
    percentages = [value for key, value in percentages.items()] # [70,10,20]
    bias_scores = percentages

    classification_index = percentages.index(max(percentages))
    classification_names = {
        'en': ['Left', 'Center', 'Right'],
        'es': ['Izquierda', 'Centro', 'Derecha'],
        'zh': ['左翼', '中立', '右翼'],
        'ko': ['좌파', '중도', '우파']
    }
    lang_labels = classification_names.get(language, classification_names['en'])
    classification = lang_labels[classification_index]

    for i in range(len(percentages)):
        percentages[i] = str(percentages[i])
    percentages = "[" + ", ".join(percentages) + "]"
    return classification, percentages, bias_scores


def read_docs(file_path):
    doc = Document(file_path)
    full_text = []
    for paragraph in doc.paragraphs:
        full_text.append(paragraph.text)

    return '\n'.join(full_text)

def read_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

# def get_keywords(text): #
#     kw_extractor = yake.KeywordExtractor(lan ="en", n=1, dedupLim = 0.9, top=5)
#     keywords = kw_extractor.extract_keywords(text)
#     keywords_lst = []
#     for keyword, score in keywords:
#         keywords_lst.append(keyword)
#     return keywords_lst
def get_keywords(text, language='en'):
    classification_prompt = (
        "Extract 3-5 broad topic categories or key entities from this news article. "
        "Focus on general themes, not specific details or events.\n\n"
        "Rules:\n"
        "- Extract main ENTITIES: important people, countries, cities, organizations (e.g., 'Donald Trump', 'United States', 'New York', 'Democratic Party', 'United Nations')\n"
        "- Extract main TOPICS: broad subject areas (e.g., 'Politics', 'Economics', 'Sports', 'Technology', 'Climate', 'Healthcare')\n"
        "- Avoid: specific events, dates, very detailed phrases\n"
        "- Avoid: actions or verbs (e.g., DON'T say 'election campaign' → SAY 'Politics')\n"
        "- Keep it simple: use general names, not descriptions\n\n"
        "Examples of GOOD keywords:\n"
        "  Article about Trump's speech in New York → Trump, New York, Politics\n"
        "  Article about France's economic policy → France, Economics, European Union\n"
        "  Article about climate summit in Glasgow → Climate, United Nations, Scotland\n\n"
        "Examples of BAD keywords (too specific):\n"
        "  ✗ 'Democratic Party Strategy' → Use 'Democratic Party' instead\n"
        "  ✗ 'New York City mayoral election' → Use 'New York' and 'Politics' instead\n"
        "  ✗ 'global warming conference proceedings' → Use 'Climate' and the location instead\n\n"
        "Article: {news_content} \n\n "
        "{lang_instruction}"
        "Keywords (comma-separated, broad categories only): "
    ).format(news_content=text, lang_instruction=get_language_instruction(language))
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0
    )
    result = response.choices[0].message.content.strip()
    print(result)
    return result

def is_news_related(prompt):
    keywords = ["news", "article", "headline","report"]
    return any(keyword in prompt.lower() for keyword in keywords)

def classify_news(news_content): # news_content = "today, trumps ~~~~~"
    classification_prompt = (
        "classify the news as left/right/center and give bias percentages for each category (for example, 30 percent left, 40 percent center and 30 percent right). give reasons to why:"
        # "If this is news, then classify the following news article as 'left', 'right' or 'center' if it is possible give the reason: \n"
        "Article: {news_content} \n\n "
        "Classification: "
    ). format(news_content = news_content)

    responses = []
    for _ in range(5):
        response = client.chat.completions.create(
            model = "gpt-4",
            messages = [{"role": "user", "content": classification_prompt}],
            temperature = 0   # Low temperature creates deterministic response
        )
        responses.append(response.choices[0].message.content.strip()) # response ["left","left","right",...")
    # determine the most common classification
    final_classification = Counter(responses).most_common(1)[0][0]
    return final_classification

def summarize_news(news_content, language='en'):
    classification_prompt = (
        "Simplify and summarize the news for an easy-to-read, shorter, and overall more convenient article. Don't cut too many points or words, preserve style, major viewpoints, theses, and ideas, but summarize it for people who may not understand or have time to read the full article:\n"
        "Article: {news_content} \n\n "
        "{lang_instruction}"
    ).format(news_content=news_content, lang_instruction=get_language_instruction(language))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

def reason_news(news_content, bias_class, language='en'):
    classification_prompt = (
        "Following news article seems to have a {bias_class} bias politically. Write a maximum of 3 sentences on why this is the case.\n"
        "Article: {news_content} \n\n "
        "{lang_instruction}"
    ).format(news_content=news_content, bias_class=bias_class, lang_instruction=get_language_instruction(language))

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()



def detect_article_language(text):
    """Detect if article is primarily in English, Spanish, Chinese, or Korean."""
    try:
        sample = text[:500]
        
        # Chinese - check for CJK characters
        if any(ord(c) >= 0x4e00 and ord(c) <= 0x9fff for c in sample):
            return "zh"
        
        # Korean - check for Hangul characters
        if any(ord(c) >= 0xac00 and ord(c) <= 0xd7af for c in sample):
            return "ko"
        
        lowered = sample.lower()
        spanish_hits = 0
        english_hits = 0

        for token in (" el ", " la ", " los ", " las ", " de ", " del ", " que ", " y ", " en ", " por ", " para ", " con ", " una ", " un ", " al ", " se ", " no "):
            if token in f" {lowered} ":
                spanish_hits += 1

        for token in (" the ", " and ", " of ", " to ", " in ", " that ", " is ", " for ", " with ", " on ", " as ", " are "):
            if token in f" {lowered} ":
                english_hits += 1

        if spanish_hits > english_hits and spanish_hits >= 2:
            return "es"

        # English/Spanish default
        return "en"
    except:
        return "en"

def clean_article_content(article_text):
    """
    Use AI to clean article text by removing ads, navigation, and noise.
    Preserves article content, images, and context.
    """
    clean_prompt = f"""
    Clean this article text by removing:
    - Ads and promotional content
    - Navigation/menu text
    - Copyright/footer boilerplate
    - "Click to read more" type phrases
    - Social media buttons
    - Duplicate content
    
    Keep:
    - Main article content
    - Relevant paragraphs
    - Image descriptions (marked with [IMAGE: ...])
    - Headers and structure
    - Important context
    
    Return only the cleaned article text, maintaining proper formatting and line breaks.
    Do NOT add explanations or metadata.
    
    Article to clean:
    ---
    {article_text}
    ---
    
    Cleaned article:
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": clean_prompt}],
        temperature=0
    )
    return response.choices[0].message.content.strip()

def extract_learning_points(article_text, article_language='en', ui_language='en'):
    """
    Extract vocabulary, idioms, and grammar patterns from article for language learning.
    Returns list of dictionaries with learning annotations.
    """
    print(f"[EXTRACT_LEARNING] Starting extraction for article language: {article_language}, ui language: {ui_language}, text length: {len(article_text)}")
    article_lang_name = LANGUAGE_NAMES.get(article_language, 'English')
    ui_lang_name = LANGUAGE_NAMES.get(ui_language, 'English')
    
    extraction_prompt = f"""
    Analyze this {article_lang_name} article to extract learning terms.
    Return each term in {article_lang_name} only. Do not mix in {ui_lang_name} or add translations, English glosses, parentheticals, or slash-separated variants to the term itself.
    For grammar patterns, keep the term as the exact {article_lang_name} structure that appears in the article.
    Provide definitions/explanations in English only.
    
    Extract:
    1. **New vocabulary** - 5-7 words/phrases learners should know (common terms, not too difficult)
    2. **Idioms/expressions** - 2-3 common idioms or fixed expressions used in the article
    3. **Grammar patterns** - 1-2 interesting grammar structures that appear in the article

    Rules:
    - Include idioms and grammar only when they are genuinely helpful to learn.
    - Do not invent idioms. If the phrase is just literal wording and not a real idiom in context, skip it.
    - Do not return partial Korean endings or dangling fragments for grammar patterns.
    - For Korean grammar, keep the exact study form from the article. If the pattern is unclear or feels incomplete, skip it.
    - Never output standalone fragments; skip them instead.
    
    Return ONLY valid JSON (no markdown, no explanation, no extra text):
    {{
        "terms": [
            {{
                "term": "word or phrase from article, written only in {article_lang_name}",
                "type": "vocabulary|idiom|grammar",
                "definition": "clear explanation in English",
                "english_meaning": "English translation or explanation",
                "part_of_speech": "noun|verb|adjective|adverb|expression|pattern",
                "example_sentence": "exact sentence from article where it appears",
                "difficulty": "beginner|intermediate|advanced",
                "grammar_note": "null or brief explanation of grammar pattern"
            }}
        ]
    }}
    
    IMPORTANT:
    - Every term MUST appear in the article
    - Definitions should be clear and simple
    - Include the exact context/sentence where term appears
    - Difficulty should be realistic for language learners
    - For grammar patterns, explain what makes it interesting/useful
    
    Article:
    {article_text[:3000]}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": extraction_prompt}],
            temperature=0
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Try to parse JSON
        import json
        
        # Handle markdown code blocks
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        
        result_json = json.loads(result_text)
        
        # Validate and clean up terms
        terms = result_json.get("terms", [])
        cleaned_terms = []
        print(f"[EXTRACT_LEARNING] Raw terms from GPT: {len(terms)}")

        for term in terms:
            # Ensure all required fields exist
            if all(k in term for k in ["term", "type", "definition", "example_sentence"]):
                term_type = term.get("type", "vocabulary").lower()
                normalized_term = (term.get("term", "") or "").strip()
                example_sentence = term.get("example_sentence", "").strip()
                if not normalized_term or not example_sentence:
                    continue
                if normalized_term not in example_sentence:
                    continue
                cleaned_terms.append({
                    "term": normalized_term,
                    "type": term_type,
                    "definition": term.get("definition", "").strip(),
                    "english_meaning": term.get("english_meaning", "").strip(),
                    "part_of_speech": term.get("part_of_speech", "").strip(),
                    "example_sentence": example_sentence,
                    "difficulty": term.get("difficulty", "intermediate").lower(),
                    "grammar_note": term.get("grammar_note")
                })
        
        print(f"[EXTRACT_LEARNING] Cleaned terms: {len(cleaned_terms)}")
        return cleaned_terms
    
    except json.JSONDecodeError as e:
        print(f"[EXTRACT_LEARNING] Failed to parse learning points JSON: {e}")
        print(f"[EXTRACT_LEARNING] Raw response: {result_text[:500]}")
        return []
    except Exception as e:
        print(f"[EXTRACT_LEARNING] Error extracting learning points: {e}")
        import traceback
        traceback.print_exc()
        return []


# classify_news("")

def get_response(prompt, model="gpt-3.5-turbo"):
    validation_prompt = f"Is the following text contains word 'news'? Answer with 'yes' or 'no'. \n\n {prompt}"
    validation_messages = [{"role": "user", "content": validation_prompt}]
    # role: specifies the role of the entity providing the message

    validation_response = client.chat.completions.create(
        model=model,
        messages=validation_messages,
        temperature=0
    )
    validation_result = validation_response.choices[0].message.content.strip().lower()
    print(validation_result)
    if validation_result == "yes":
        # content: contains actual prompt text that the user wants the model to respond to

        classification = f"Please classify the following news as either 'left' or 'right' based on the news content: \n\n {prompt}"
        messages = [{"role": "user", "content": classification}]

        # client.chat.completions.create --> For creating a response from chatGPT
        response = client.chat.completions.create(
            model = model,
            messages = messages,
            temperature = 0 # Score (0~1)
            # if temperature is low  --> it will generate more predictable response
            # if temperature is high --> it generates more random but creative response
        )
        return response.choices[0].message.content
    else:
        return "We cannot answer to your question because we only answer to the news-related questions"
def calculate_sentiment_subject(text):
    # Textblob is a library for getting plorarity and subjectivity score of the given text
    blob = TextBlob(text)
    sentiment = blob.sentiment
    return {"ploarity":sentiment.polarity, "subjectivity":sentiment.subjectivity}

#print(calculate_sentiment_subject("i got f on my algera exam"))
# polarity: min: -1, max: 1, where -1 indicates negative sentiment, 1 is positive sentiment
# subjectivity: min: 0, max:1 where 0 is very objective, and 1 is very subjective.

# Function for getting HTML codes of the news
def fetch_article_from_url(url):
    """
    Fetch article content from a URL.
    Returns: (article_text, error_message)
    - If successful: (text, None)
    - If error: (None, error_message)
    """
    error_indicators = [
        'paywalled', 'paywall', 'subscription required', 'subscribe',
        'login', 'sign in', 'access denied', 'forbidden',
        'premium', 'members only', 'exclusive'
    ]
    
    try:
        # Set a realistic user agent to avoid blocking
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        
        # Check HTTP status
        if response.status_code == 403:
            return None, "Access denied. Article may be region-restricted or require authentication."
        elif response.status_code == 404:
            return None, "Article not found. Please check the URL."
        elif response.status_code >= 400:
            return None, f"Unable to fetch article (HTTP {response.status_code}). Website may be blocking automated access."
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Check for paywall indicators in HTML
        page_text = soup.get_text().lower()
        for indicator in error_indicators:
            if indicator in page_text:
                # Do a more thorough check
                if 'paywall' in indicator or 'subscription' in indicator or 'premium' in indicator:
                    # Might actually be paywalled
                    if page_text.count(indicator) > 2:  # If mentioned multiple times
                        return None, "This article appears to be behind a paywall. Please try copying the text directly or accessing via an archive service."
        
        # Extract article text - try common article containers
        article_text = None
        
        # Try common selectors
        selectors = [
            'article',
            '[role="main"]',
            '.article-body',
            '.article-content',
            '.post-content',
            '.entry-content',
            '.content',
            'main'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                article_text = element.get_text(strip=True)
                if len(article_text) > 200:  # Minimum article length
                    break
        
        # Fallback: use body text if no article element found
        if not article_text:
            body = soup.body
            if body:
                # Remove script and style elements
                for script in body(['script', 'style', 'nav', 'footer']):
                    script.decompose()
                article_text = body.get_text(strip=True)
        
        # Clean up the text
        if article_text:
            # Remove extra whitespace and newlines
            article_text = '\n'.join(line.strip() for line in article_text.split('\n') if line.strip())
            
            # Minimum length check
            if len(article_text) < 100:
                return None, "Article text is too short or could not be extracted. This may be a paywalled or restricted article."
            
            return article_text, None
        else:
            return None, "Unable to extract article content. The website structure may not be supported."
    
    except requests.exceptions.Timeout:
        return None, "Request timed out. The website is taking too long to respond."
    except requests.exceptions.ConnectionError:
        return None, "Connection error. Please check the URL and your internet connection."
    except requests.exceptions.RequestException as e:
        return None, f"Error fetching URL: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"


def getting_news(link):
    try:
        # Accessing to the given link'
        print("hello")
        response = requests.get(link)
        print("hello")
        # Code 200 --> suessfully accesed to the website.
        if response.status_code == 200:
            # Extract the HTML from the given link

            html_content = response.text
            soup = BeautifulSoup(html_content, 'html.parser')
            body_tag = soup.body
            if 'washingtonpost' in link:
                main_content = body_tag.article
                return main_content.text

    except requests.execeptions.RequestException as e:
        print(f"Error: {e}")
# print()