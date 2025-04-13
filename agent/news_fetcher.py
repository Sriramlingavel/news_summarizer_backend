import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import trafilatura

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def fetch_news(topic: str):
    url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return [f"Error fetching news: {response.status_code}"]

    articles = response.json().get("articles", [])
    return [f"{article['title']}\n{article['content']}" for article in articles[:3] if article['content']]

def fetch_article_content(url):
    """
    Fetch the content of an article from a URL.
    
    Args:
        url: The URL of the article
        
    Returns:
        The extracted article text
    """
    try:
        # Try using trafilatura first (better content extraction)
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            article_text = trafilatura.extract(downloaded)
            if article_text:
                return article_text
        
        # Fallback to BeautifulSoup
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
        
        # Get text
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space on each
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text
    except Exception as e:
        print(f"Error fetching article: {str(e)}")
        return f"Error fetching article: {str(e)}"