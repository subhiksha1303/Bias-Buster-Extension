import re
import requests
import json
import os
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
import nltk
from textblob import TextBlob  # For sentiment analysis

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

# 🔹 Trusted news sources based on domain names
TRUSTED_SOURCES = [
    "bbc.com", "cnn.com", "thehindu.com", "ndtv.com",
    "reuters.com", "theguardian.com", "nytimes.com",
    "indiatoday.in", "hindustantimes.com", "forbes.com",
    "bloomberg.com", "wsj.com", "apnews.com", "abcnews.go.com",
    "foxnews.com", "nbcnews.com", "cbsnews.com", "sky.com",
]

def is_trusted_source(url):
    """Check if the URL belongs to a trusted source."""
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace("www.", "")
    return domain in TRUSTED_SOURCES

NEWS_API_KEY = "e242defe23904eee96b22acfb4d1ecee"
NEWS_API_URL = "https://newsapi.org/v2/everything"

def extract_keywords(text):
    """Extract important keywords from the news text."""
    words = re.findall(r'\b\w+\b', text)
    stopwords = {"the", "is", "in", "a", "an", "on", "of", "and", "to", "for", "with"}
    keywords = [word for word in words if word.lower() not in stopwords]
    return " ".join(keywords[:8])

def fetch_news_from_newsapi(query):
    """Fetch news articles from NewsAPI based on query."""
    params = {"q": query, "apiKey": NEWS_API_KEY, "language": "en", "sortBy": "relevancy", "pageSize": 10}
    response = requests.get(NEWS_API_URL, params=params)
    
    if response.status_code != 200:
        return {"status": "error", "message": "Failed to fetch news from NewsAPI."}
    
    return response.json().get("articles", [])

def analyze_sentiment(text):
    """Analyze sentiment polarity using TextBlob."""
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity
    if polarity > 0.1:
        return "Positive"
    elif polarity < -0.1:
        return "Negative"
    else:
        return "Neutral"

# List of harsh/subjective words to remove
HARSH_WORDS = {
    "terrible", "horrible", "awful", "disgusting", "amazing", "fantastic", "incredible",
    "hate", "love", "worst", "best", "stupid", "idiot", "brilliant", "perfect"
}

def remove_harsh_words(text):
    """Remove harsh words to generate a neutral summary."""
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in HARSH_WORDS]
    return " ".join(filtered_words)

def generate_objective_summary(text):
    """Create an unbiased summary using the first few sentences."""
    cleaned_text = remove_harsh_words(text)
    sentences = re.split(r'(?<=[.!?]) +', cleaned_text)
    summary = " ".join(sentences[:5])  # Take first 5 sentences
    return summary

@api_view(["GET", "POST"])
@csrf_exempt
def analyze_news(request):
    """Analyze news, check legitimacy, summarize, and show other perspectives."""
    if request.method == "GET":
        return render(request, "index.html")

    if request.method != "POST":
        return JsonResponse({"status": "error", "message": "Invalid request method."}, status=400)

    try:
        data = json.loads(request.body)
        news_text = data.get("news_text", "").strip()

        if not news_text:
            return JsonResponse({"status": "error", "message": "News text is required."}, status=400)

        keyword_query = extract_keywords(news_text)
        articles = fetch_news_from_newsapi(keyword_query)

        perspectives = []
        trusted_source_count = 0
        trusted_articles = []

        if articles:
            for article in articles[:5]:  
                source_url = article.get("url", "")
                source_name = article.get("source", {}).get("name", "Unknown")
                is_trusted = is_trusted_source(source_url)

                if is_trusted:
                    trusted_source_count += 1
                    trusted_articles.append({
                        "source": source_name,
                        "title": article.get("title", ""),
                        "url": source_url,
                    })

                perspectives.append({
                    "source": source_name,
                    "title": article.get("title", ""),
                    "url": source_url,
                    "sentiment": analyze_sentiment(article.get("content", ""))
                })

            # Generate an objective summary
            objective_summary = generate_objective_summary(news_text)

            # Determine if the news is legit
            is_legit = trusted_source_count >= 2  # If at least 2 trusted sources report it, mark as legit

            return JsonResponse({
                "status": "real" if is_legit else "fake",
                "bias_score": analyze_sentiment(news_text),  
                "objective_summary": objective_summary,
                "message": "News verification complete. Perspectives found:",
                "trusted_articles": trusted_articles,  # Legit news articles from trusted sources
                "perspectives": perspectives,  # Other views
            })

        return JsonResponse({"status": "fake", "message": "No reliable sources found."})

    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON input."}, status=400)
