import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
from dotenv import load_dotenv
from flask_caching import Cache

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Flask-Caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Load API key from .env
NEWS_API_KEY = os.getenv('NEWS_API_KEY')

@app.route('/')
def index():
    return render_template('index.html')

@cache.memoize(timeout=300)  # Cache the results for 5 minutes (300 seconds)
@app.route('/fetch-news', methods=['POST'])
def fetch_news():
    topic = request.json.get('topic', '')
    sources = request.json.get('sources', '')

    # Build the API request URL
    if sources:  # If sources are provided, filter results
        url = f'https://newsapi.org/v2/everything?q={topic}&sources={sources}&apiKey={NEWS_API_KEY}'
    else:  # If no sources are provided, fetch from all available sources
        url = f'https://newsapi.org/v2/everything?q={topic}&apiKey={NEWS_API_KEY}'

    response = requests.get(url)

    if response.status_code != 200:
        return jsonify({"error": "Error fetching news from API"}), response.status_code

    articles = response.json().get('articles', [])

    result = []
    for article in articles:
        result.append({
            'title': article.get('title'),
            'author': article.get('author'),
            'date': article.get('publishedAt'),
            'source': article.get('source', {}).get('name', 'Unknown Source'),
            'link': article.get('url'),
            'summary': article.get('description') or 'No summary available'
        })

    return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True)