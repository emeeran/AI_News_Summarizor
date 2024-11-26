import os
import logging
import requests
import streamlit as st
import base64
from dotenv import load_dotenv
from groq import Groq
from gtts import gTTS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s')

# Load environment variables
load_dotenv()

# Retrieve and validate API keys
NEWS_API_KEY = os.getenv("NEWS_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not all([NEWS_API_KEY, GROQ_API_KEY]):
    raise ValueError("Missing API keys. Please check your .env file.")

class NewsAnalyzer:
    def __init__(self, model='llama3-8b-8192'):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.model = model

    def summarize(self, news_articles: list, topic: str) -> str:
        news_content = "\n\n".join(news_articles)
        prompt = (
            f"You are an expert news analyst summarizing articles about '{topic}'. "
            "Provide a comprehensive, objective summary that:\n"
            "1. Synthesizes key points from multiple news sources\n"
            "2. Highlights the most significant insights\n"
            "3. Maintains a neutral, journalistic tone\n"
            "4. Covers the broader context and implications\n"
            "5. Keeps the summary concise (250-300 words)\n\n"
            "News Articles:\n"
            f"{news_content}"
        )

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert news analyst."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=350,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logging.error(f"Summarization error: {e}")
            return f"Error generating summary: {str(e)}"

def fetch_news(topic: str, page_size: int = 5) -> list:
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
            (
                f"**{article.get('title', 'No Title Available')}**\n"
                f"*Source:* {article.get('source', {}).get('name', 'Unknown Source')}\n"
                f"*Author:* {article.get('author', 'Anonymous')}\n"
                f"*Published:* {article.get('publishedAt', 'Unknown Date')}\n"
                f"*Description:* {article.get('description', 'No Description Available')}\n"
                f"[Read Full Article]({article.get('url', '#')})"
            )
            for article in news_data.get("articles", [])[:page_size]
        ]
    except requests.RequestException as e:
        st.error(f"News API Error: {e}")
        return []

def text_to_speech(text: str, filename: str = 'summary.mp3') -> str:
    try:
        tts = gTTS(text=text, lang='en')
        os.makedirs('audio', exist_ok=True)
        filepath = os.path.join('audio', filename)
        tts.save(filepath)
        return filepath
    except Exception as e:
        st.error(f"Text-to-Speech conversion error: {e}")
        return None

def get_audio_player(audio_file):
    with open(audio_file, 'rb') as audio_file:
        audio_bytes = audio_file.read()
    base64_audio = base64.b64encode(audio_bytes).decode('utf-8')
    return f"""
        <audio controls autoplay style="width: 100%;">
            <source src="data:audio/mp3;base64,{base64_audio}" type="audio/mp3">
            Your browser does not support the audio element.
        </audio>
    """

def main():
    st.set_page_config(
        page_title="Groq News Summarizer",
        page_icon="📰",
        layout="wide"
    )

    with st.sidebar:
        st.header("🛠 Configuration")
        models = [
            'llama3-8b-8192',
            'mixtral-8x7b-32768',
            'gemma-7b-it'
        ]
        selected_model = st.selectbox(
            "Select Groq Model",
            models,
            index=0,
            help="Choose the Groq language model for summarization"
        )
        st.markdown("---")
        st.info(
            "💡 Tips:\n"
            "- Enter broad or specific topics\n"
            "- Try different Groq models\n"
            "- Explore global news trends"
        )

    st.title("🌐 Groq News Summarizer")
    st.markdown("Get AI-generated summaries of the latest news using Groq's advanced language models.")

    topic = st.text_input(
        "Enter News Topic",
        placeholder="e.g., AI Innovation, Climate Change, Global Politics",
        help="Enter a broad or specific news topic"
    )

    search_button = st.button("Summarize News")

    if search_button and topic:
        with st.spinner(f"Fetching and analyzing news about '{topic}'..."):
            news_articles = fetch_news(topic)

            if not news_articles:
                st.warning("No recent news articles found. Try a different topic.")
                return

            try:
                analyzer = NewsAnalyzer(model=selected_model)
                summary = analyzer.summarize(news_articles, topic)

                st.subheader(f"News Summary: {topic}")
                st.markdown(f"*Generated using Groq - {selected_model}*")
                st.markdown(summary)

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.subheader("🔊 Listen to Summary")

                audio_file = text_to_speech(summary)
                if audio_file:
                    with col2:
                        if st.download_button(
                            label="Download Audio",
                            data=open(audio_file, 'rb').read(),
                            file_name="news_summary.mp3",
                            mime="audio/mp3"
                        ):
                            st.success("Audio file downloaded!")

                    st.components.v1.html(get_audio_player(audio_file), height=70)

                with st.expander("Original News Sources"):
                    for article in news_articles:
                        st.markdown(article)
                        st.markdown("---")

            except Exception as e:
                st.error(f"Summarization failed: {e}")

if __name__ == "__main__":
    main()
