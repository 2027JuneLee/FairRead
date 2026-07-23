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

api_key = "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"
client = OpenAI(api_key=api_key)

# tokenizer = AutoTokenizer.from_pretrained("bucketresearch/politicalBiasBERT")
# model = AutoModelForSequenceClassification.from_pretrained("bucketresearch/politicalBiasBERT")
#
# summarizer = pipeline('summarization', model="facebook/bart-large-cnn")

# function for summarizing text
def summarize_text(text, max_length=1000, min_length=30):
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


def get_bias_classification(text):
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

    classification = percentages.index(max(percentages))
    if classification == 0:
        classification = "Left"
    elif classification == 1:
        classification = "Center"
    else:
        classification = "Right"

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
def get_keywords(text):
    classification_prompt = (
        "Classify the news article into 3 to 5 main topics, issues, or keywords. For example, focus on the place the news takes place in, who it mainly involve, which topic the news is about, and the event of the news, such as 'politics', 'Cuba', 'Donald Trump', and 'assassination.' Put quotation marks like '' for each keyword: "
        "Provide the keywords as a comma-separated list."
        "Example format: 'keyword1', 'keyword2', 'keyword3', 'keyword4', 'keyword5'\n\n"
        f"Text: {text}\n\n"
        "Output:"
    )
    classification_prompt = (
        "Classify the news article into 3 to 5 main topics, issues, or keywords. For example, focus on the place the news takes place in, who it mainly involve, which topic the news is about, and the event of the news, such as 'politics', 'Cuba', 'Donald Trump', and 'assassination': \n"
        "Article: {news_content} \n\n "
        "Keywords: "
    ).format(news_content = text)
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

def summarize_news(news_content): # news_content = "today, trumps ~~~~~"
    classification_prompt = (
        "Simplify and summarize the news for an easy-to-read, shorter, and overall more convenient article. Don't cut too many points or words, preserve style, major viewpoints, theses, and ideas, but summarize it for people who may not understand or have time to read the full article:\n"
        "Article: {news_content} \n\n "
    ).format(news_content = news_content)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0  # Low temperature creates deterministic response
    )
    return response.choices[0].message.content.strip()

def reason_news(news_content, bias_class): # news_content = "today, trumps ~~~~~"
    classification_prompt = (
        "Following news article seems to have a {bias_class} bias politically. Write a maximum of 3 sentences on why this is the case/ \n"
        "Article: {news_content} \n\n "
    ).format(news_content = news_content, bias_class = bias_class)

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": classification_prompt}],
        temperature=0  # Low temperature creates deterministic response
    )
    return response.choices[0].message.content.strip()



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
# text = getting_news("https://www.washingtonpost.com/politics/2024/08/24/trump-energy-campaign-harris/")
# # text = read_docs("sample.docx")
# print("done extracting")
# bias_class, bias_scores = get_bias_classification(text)
# summary = summarize_news(text)
# reason = reason_news(text, bias_class)
# print(f"Bias Class: {bias_class}")
# print(f"Bias Scores: {bias_scores}")
# print(f"Reason: {reason}")
# print(f"Summary: {summary}")
# print()