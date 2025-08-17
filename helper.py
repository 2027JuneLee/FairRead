from newspaper import Article

def extract_news_content(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        return article.text
    except Exception as e:
        print("Error", e)
        return None
