import os
import logging
import time
import json
import requests
import streamlit as st
import openai
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Load environment variables
load_dotenv()

# Retrieve API keys with error checking
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not NEWS_API_KEY or not OPENAI_API_KEY:
    st.error("Missing API keys. Please configure your .env file.")
    st.stop()

# Configure OpenAI client
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def get_news(topic: str, page_size: int = 5) -> list:
    """
    Fetch news articles for a given topic.

    :param topic: Topic to search for
    :param page_size: Number of articles to retrieve
    :return: List of formatted news articles
    """
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": topic,
        "apiKey": NEWS_API_KEY,
        "pageSize": page_size,
        "sortBy": "publishedAt"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()

        news_data = response.json()

        final_news = []
        for article in news_data.get("articles", []):
            news_item = {
                "title": article.get("title", "N/A"),
                "author": article.get("author", "Unknown"),
                "source": article.get("source", {}).get("name", "N/A"),
                "description": article.get("description", ""),
                "url": article.get("url", "")
            }

            final_news.append(
                f"Title: {news_item['title']}\n"
                f"Author: {news_item['author']}\n"
                f"Source: {news_item['source']}\n"
                f"Description: {news_item['description']}\n"
                f"URL: {news_item['url']}"
            )

        return final_news

    except requests.RequestException as e:
        logging.error(f"News API request failed: {e}")
        st.error(f"Could not fetch news: {e}")
        return []

class NewsSummarizer:
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the NewsSummarizer with OpenAI client and model.

        :param model: OpenAI model to use for summarization
        """
        self.client = client
        self.model = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.summary = None

    def create_assistant(self, topic: str) -> str:
        """
        Create an AI assistant specialized for news summarization.

        :param topic: Topic of the news for context
        :return: Assistant ID
        """
        try:
            self.assistant = self.client.beta.assistants.create(
                name=f"News Summarizer - {topic}",
                instructions=(
                    "You are an expert news analyst. "
                    "Provide a concise, objective summary of the news articles. "
                    "Highlight key points, main themes, and significant insights. "
                    "Maintain a neutral, informative tone."
                ),
                model=self.model,
                tools=[{
                    "type": "function",
                    "function": {
                        "name": "get_news",
                        "description": "Retrieve latest news articles on a specific topic",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "topic": {
                                    "type": "string",
                                    "description": "The news topic to search"
                                }
                            },
                            "required": ["topic"]
                        }
                    }
                }]
            )
            return self.assistant.id
        except Exception as e:
            logging.error(f"Assistant creation failed: {e}")
            st.error(f"Could not create assistant: {e}")
            return None

    def create_thread(self) -> str:
        """
        Create a new conversation thread.

        :return: Thread ID
        """
        try:
            self.thread = self.client.beta.threads.create()
            return self.thread.id
        except Exception as e:
            logging.error(f"Thread creation failed: {e}")
            st.error(f"Could not create conversation thread: {e}")
            return None

    def add_news_to_thread(self, news_articles: list, topic: str):
        """
        Add news articles to the conversation thread.

        :param news_articles: List of news article summaries
        :param topic: News topic
        """
        if not self.thread:
            raise ValueError("Thread not initialized")

        try:
            news_content = f"News Summary for '{topic}':\n\n" + "\n\n".join(news_articles)

            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=news_content
            )
        except Exception as e:
            logging.error(f"Failed to add news to thread: {e}")
            st.error(f"Could not process news articles: {e}")

    def summarize_news(self) -> str:
        """
        Run the assistant to summarize news articles.

        :return: News summary
        """
        if not self.thread or not self.assistant:
            raise ValueError("Thread or Assistant not initialized")

        try:
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id,
                instructions="Provide a comprehensive, concise summary of the news articles."
            )

            # Wait for run completion
            while run.status not in ["completed", "failed"]:
                time.sleep(3)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=run.id
                )

            if run.status == "completed":
                messages = self.client.beta.threads.messages.list(thread_id=self.thread.id)
                for msg in messages.data:
                    if msg.role == "assistant":
                        return msg.content[0].text.value

                return "No summary generated."
            else:
                st.error("News summarization failed.")
                return None

        except Exception as e:
            logging.error(f"News summarization error: {e}")
            st.error(f"Could not summarize news: {e}")
            return None

def main():
    st.set_page_config(
        page_title="News Summarizer",
        page_icon="📰",
        # layout="wide"
    )

    st.title("🌐 AI-Powered News Summarizer")

    # User input
    with st.form(key="news_search_form"):
        topic = st.text_input(
            "Enter a news topic",
            placeholder="e.g., Climate Change, AI Technology, Global Politics",
            help="Enter a topic to get the latest news summary"
        )
        submit_button = st.form_submit_button("Get News Summary")

    # News processing
    if submit_button and topic:
        with st.spinner(f"Fetching and analyzing news about '{topic}'..."):
            # Fetch news articles
            news_articles = get_news(topic)

            if not news_articles:
                st.warning("No recent news articles found. Try a different topic.")
                return

            # Initialize summarizer
            summarizer = NewsSummarizer()

            # Create assistant
            if summarizer.create_assistant(topic):
                # Create thread
                if summarizer.create_thread():
                    # Add news to thread
                    summarizer.add_news_to_thread(news_articles, topic)

                    # Generate summary
                    summary = summarizer.summarize_news()

                    if summary:
                        # Display results
                        st.subheader(f"News Summary: {topic}")
                        st.markdown(summary)

                        # Expander for original articles
                        with st.expander("Original News Articles"):
                            for article in news_articles:
                                st.markdown(article)
                    else:
                        st.error("Failed to generate news summary.")

if __name__ == "__main__":
    main()