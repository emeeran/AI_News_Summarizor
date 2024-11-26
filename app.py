from flask import Flask, render_template, request, jsonify
from datetime import datetime
import requests
import html
import re
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# API Keys and URLs
NEWS_API_KEY = "d2b4ffeb2bc14b02b97a2279d4d5628b"
NEWS_API_URL = "https://newsapi.org/v2/everything"
HINDU_API_URL = "https://the-hindu-national-news.p.rapidapi.com/api/news"
HINDU_API_KEY = "RAPID_API_KEY"

HINDU_HEADERS = {
    "X-RapidAPI-Key": HINDU_API_KEY,
    "X-RapidAPI-Host": "the-hindu-national-news.p.rapidapi.com",
}


def get_summary(text, num_lines=3):
    """
    Summarizes the input text into the specified number of sentences.
    """
    if not text:
        return "Summary not available."

    text = clean_html(text)
    sentences = re.split(r'[.!?]+', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    summary = ". ".join(sentences[:num_lines]) + "."
    return summary if summary.strip() else "Summary not available."


def clean_html(text):
    """
    Cleans HTML entities and tags from the given text.
    """
    if not text:
        return ""
    text = html.unescape(text)
    return re.sub(r"<[^>]+>", "", text)


def fetch_hindu_news():
    """
    Fetches news articles from The Hindu API.
    """
    try:
        response = requests.get(HINDU_API_URL, headers=HINDU_HEADERS, timeout=10)
        response.raise_for_status()
        hindu_data = response.json()

        return [
            {
                "title": clean_html(article.get("title", "")),
                "url": article.get("url", ""),
                "source": "The Hindu",
                "published_at": format_date(article.get("published_date", "")),
                "summary": get_summary(article.get("description", "")),
                "image_url": article.get("image_url", ""),
                "author": article.get("author", "The Hindu"),
            }
            for article in hindu_data.get("data", [])
            if article.get("title") and article.get("url")
        ]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching The Hindu news: {e}")
        return []


def fetch_news_api_articles(topic):
    """
    Fetches news articles from the News API for a given topic.
    """
    params = {
        "q": topic,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "pageSize": 10,
        "sortBy": "publishedAt",
    }

    try:
        response = requests.get(NEWS_API_URL, params=params, timeout=10)
        response.raise_for_status()
        news_data = response.json()

        return [
            {
                "title": clean_html(article.get("title", "")),
                "url": article.get("url", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": format_date(article.get("publishedAt", "")),
                "summary": get_summary(article.get("description", "")),
                "image_url": article.get("urlToImage", ""),
                "author": article.get("author", "Unknown"),
            }
            for article in news_data.get("articles", [])
            if article.get("title") and article.get("url")
        ]
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news API articles: {e}")
        return []


def merge_and_sort_news(topic_news, hindu_news):
    """
    Merges and sorts articles from both APIs by published date.
    """
    return sorted(topic_news + hindu_news, key=lambda x: x["published_at"], reverse=True)


@app.route("/", methods=["GET", "POST"])
def home():
    default_topics = [
        "Technology",
        "Health",
        "Sports",
        "Business",
        "Science",
        "Entertainment",
        "Politics",
        "Environment",
    ]
    news_articles = []
    error_message = None
    selected_topic = ""

    if request.method == "POST":
        topic = request.form.get("topic", "").strip() or request.form.get("custom_topic", "").strip()
        selected_topic = topic

        if topic:
            # Concurrently fetch articles
            with ThreadPoolExecutor(max_workers=2) as executor:
                topic_future = executor.submit(fetch_news_api_articles, topic)
                hindu_future = executor.submit(fetch_hindu_news)

                topic_news = topic_future.result()
                hindu_news = hindu_future.result()

            news_articles = merge_and_sort_news(topic_news, hindu_news)
            if not news_articles:
                error_message = f"No news articles found for the topic: {topic}"
        else:
            error_message = "Please select or enter a topic."

    return render_template(
        "index.html",
        default_topics=default_topics,
        news_articles=news_articles,
        error_message=error_message,
        selected_topic=selected_topic,
    )


def format_date(date_str):
    """
    Formats the given date string into a more readable format.
    """
    if not date_str:
        return ""
    for fmt in ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
        try:
            return datetime.strptime(date_str, fmt).strftime("%B %d, %Y %I:%M %p")
        except ValueError:
            continue
    return date_str


if __name__ == "__main__":
    app.run(debug=True)
