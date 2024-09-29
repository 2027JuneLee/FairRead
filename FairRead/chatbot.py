from openai import OpenAI
from textblob import TextBlob
import requests
from bs4 import BeautifulSoup

client = OpenAI(api_key="")

def get_response(prompt, model="gpt-3.5-turbo"):
    validation_prompt = f"Does the following text contain the word 'news?' Answer with 'yes' or 'no'. \n\n{prompt}"
    #validation_prompt = f"Please classify the user's inputed news as either moderate/solid/far/slight left-wing, moderate/solid/far/slight right-wing, or factual/scientific. Provide a few key viewpoints and reasons why for the news. \n\n{prompt}"
    validation_messages = [{"role":"user","content":validation_prompt}]

    validation_response = client.chat.completions.create(
        model = model,
        messages=validation_messages,
        temperature=0
    )
    validation_result = validation_response.choices[0].message.content.strip().lower()
    if validation_result == "yes":

        classification = f"Please classify the user's inputed news text as either moderate/solid/far/slight left-wing, moderate/solid/far/slight right-wing, or center/nonpartisan/factual/scientific. Provide a few key viewpoints and reasons why the text has that bias."
        messages = [{"role":"user", "content": classification}] #role specifies the role of the entity providing the message, content contains the actual prompt of the user
        response = client.chat.completions.create(
            model = model,
            messages = messages,
            temperature = 0 # is the score(!) of 0 to 1, which returns more predictable responses if the temperature is low and more creative/random responses if the temperature is high
        ) #c.c.c.c: used to create a response from chatGPT

        return response.choices[0].message.content

    else:
        return "Sorry, FairRead AI only allows news-related questions."

def calculate_sentiment_subject(text):
    blob = TextBlob(text)
    sentiment = blob.sentiment
    return {"polarity":sentiment.polarity,"subjectivity":sentiment.subjectivity}

print(calculate_sentiment_subject("We all must adhere to the belief that Donald Trump is a fraud, who is an egotistical maniac and a stone-cold atrocity for our humble nation."))
print(calculate_sentiment_subject("TRUMP IS A FASCIST, EGOTISTICAL LIAR, AND WILL BE AN ATROCITY FOR OUR COUNTRY."))

def getting_news(link):
    try:
        response = requests.get(link)
        #200 = GOOD, SUCCESSFUL ENTRY TO WEBSITE
        if response.status_code == 200:
            html_content = response.text #extract html from link
            soup = BeautifulSoup(html_content, 'html.parser')
            body_tag = soup.body

            if 'washingtonpost' in link:
                main_content = body_tag.article
                return main_content.text

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")

#q = input("ENTER ANYTHING: ")
#a = get_response(q)
#print(a)