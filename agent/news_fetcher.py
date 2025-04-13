import requests
import os
from dotenv import load_dotenv

load_dotenv()
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

def fetch_news(topic: str):
    url = f"https://newsapi.org/v2/everything?q={topic}&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return [f"Error fetching news: {response.status_code}"]

    articles = response.json().get("articles", [])
    return [f"{article['title']}\n{article['content']}" for article in articles[:3] if article['content']]
