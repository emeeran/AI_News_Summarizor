import os
import logging
import time
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

def log_and_display_error(message: str, exception: Exception):
    logging.error(f"{message}: {exception}")
    st.error(f"{message}: {exception}")

def get_news(topic: str, page_size: int = 15) -> list:
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": topic,
        "apiKey": NEWS_API_KEY,
        "pageSize": page_size,
        "sortBy": "publishedAt",
        "language": "en"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        news_data = response.json()

        return [
            f"Title: {article.get('title', 'N/A')}\n"
            f"Author: {article.get('author', 'Unknown')}\n"
            f"Source: {article.get('source', {}).get('name', 'N/A')}\n"
            f"Description: {article.get('description', '')}\n"
            f"URL: {article.get('url', '')}"
            for article in news_data.get("articles", [])[:page_size]
        ]

    except requests.RequestException as e:
        log_and_display_error("News API request failed", e)
        return []

class NewsSummarizer:
    def __init__(self, model: str = "gpt-4o-mini"):
        self.client = client
        self.model = model
        self.assistant = None
        self.thread = None

    def create_assistant(self, topic: str) -> str:
        try:
            self.assistant = self.client.beta.assistants.create(
                name=f"News Summarizer - {topic}",
                instructions=(
                    "You are a helpful study assistant who knows a lot about understanding research papers. "
                    "Your role is to summarize papers, clarify terminology within context, and extract key figures and data. "
                    "Cross-reference information for additional insights and answer related questions comprehensively. "
                    "Analyze the papers, noting strengths and limitations. Respond to queries effectively, incorporating feedback to enhance your accuracy. "
                    "Handle data securely and update your knowledge base with the latest research. Adhere to ethical standards, respect intellectual property, "
                    "and provide users with guidance on any limitations. Maintain a feedback loop for continuous improvement and user support. "
                    "Your ultimate goal is to facilitate a deeper understanding of complex scientific material, making it more accessible and comprehensible."
                ),
                model=self.model,
                tools=[]
            )
            return self.assistant.id
        except Exception as e:
            log_and_display_error("Assistant creation failed", e)
            return None

    def create_thread(self) -> str:
        try:
            self.thread = self.client.beta.threads.create()
            return self.thread.id
        except Exception as e:
            log_and_display_error("Thread creation failed", e)
            return None

    def add_news_to_thread(self, news_articles: list, topic: str):
        if not self.thread:
            raise ValueError("Thread not initialized")

        try:
            news_content = (
                f"Provide a comprehensive summary for news articles about '{topic}'.\n\n"
                "News Articles:\n" +
                "\n\n".join(news_articles) +
                "\n\nImportant: Synthesize these articles into a concise, coherent summary."
            )

            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role="user",
                content=news_content
            )
        except Exception as e:
            log_and_display_error("Failed to add news to thread", e)

    def summarize_news(self, timeout: int = 90) -> str:
        if not (self.thread and self.assistant):
            raise ValueError("Thread or Assistant not initialized")

        try:
            run = self.client.beta.threads.runs.create(
                thread_id=self.thread.id,
                assistant_id=self.assistant.id,
                instructions="Provide a comprehensive, concise summary of the news articles."
            )

            start_time = time.time()

            while True:
                if time.time() - start_time > timeout:
                    log_and_display_error("News summarization timed out", Exception())
                    return None

                run = self.client.beta.threads.runs.retrieve(
                    thread_id=self.thread.id,
                    run_id=run.id
                )

                if run.status == "completed":
                    messages = self.client.beta.threads.messages.list(
                        thread_id=self.thread.id
                    )

                    assistant_message = next(
                        (msg.content[0].text.value for msg in reversed(messages.data) if msg.role == "assistant"),
                        "No summary generated."
                    )
                    return assistant_message

                elif run.status in ["failed", "cancelled"]:
                    log_and_display_error(f"Run failed with status: {run.status}", Exception())
                    return None

                time.sleep(5)

        except Exception as e:
            log_and_display_error("News summarization error", e)
            return None

def main():
    st.set_page_config(
        page_title="News Summarizer",
        page_icon="📰",
    )

    st.title("🌐 News Summarizer")

    with st.form(key="news_search_form"):
        topic = st.text_input(
            "Enter a news topic",
            placeholder="",
            help="Enter a topic to get the latest news summary"
        )
        submit_button = st.form_submit_button("Get News Summary")

    if submit_button and topic:
        with st.spinner(f"Fetching and analyzing news about '{topic}'..."):
            news_articles = get_news(topic)

            if not news_articles:
                st.warning("No recent news articles found. Try a different topic.")
                return

            summarizer = NewsSummarizer()

            if summarizer.create_assistant(topic) and summarizer.create_thread():
                summarizer.add_news_to_thread(news_articles, topic)
                summary = summarizer.summarize_news()

                if summary:
                    st.subheader(f"News Summary: {topic}")
                    st.markdown(summary)

                    with st.expander("Original News Articles"):
                        for article in news_articles:
                            st.markdown(article)
                else:
                    st.error("Failed to generate news summary.")

if __name__ == "__main__":
    main()
