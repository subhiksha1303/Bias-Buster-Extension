import requests
import re
import json
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from bs4 import BeautifulSoup  # For web scraping
from transformers import pipeline  # For AI summarization

# API Keys & Configuration
GOOGLE_API_KEY = "AIzaSyD0RJdZ3NtQAI9Y2KqSiTdcfK3a0ulMHf0"
GOOGLE_CSE_ID = "86f38c27f03df4661"

def home(request):
    return render(request, "index.html")

# AI Summarization Model
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

# Trusted news sources (can be expanded)
TRUSTED_SOURCES = [
    "bbc.com", "cnn.com", "reuters.com", "nytimes.com", "theguardian.com", "aljazeera.com",
    "thehindu.com", "ndtv.com", "indiatoday.in", "hindustantimes.com", "timesofindia.indiatimes.com",
    "deccanherald.com", "business-standard.com", "news18.com"
]

### 🔹 **Step 1: Fetch News from Google Custom Search API**
def fetch_news_google(query):
    """Fetch news articles from Google Custom Search API."""
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_API_KEY}&cx={GOOGLE_CSE_ID}"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    
    articles = response.json().get("items", [])
    return [
        {
            "source": article.get("displayLink"),
            "title": article.get("title"),
            "url": article.get("link"),
            "snippet": article.get("snippet")
        }
        for article in articles
    ]

### 🔹 **Step 2: Web Scraping for Additional News Sources**
def scrape_article(url):
    """Scrape article content from the URL."""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, "html.parser")
        paragraphs = soup.find_all("p")
        content = " ".join([p.text for p in paragraphs])
        return content if len(content) > 100 else None  # Ignore very short articles
    except:
        return None

### 🔹 **Step 3: Text Similarity Matching**
def is_similar(text1, text2):
    """Simple text similarity check using common words overlap."""
    words1, words2 = set(text1.lower().split()), set(text2.lower().split())
    overlap = words1.intersection(words2)
    return len(overlap) / min(len(words1), len(words2)) > 0.3  # 30% similarity threshold

### 🔹 **Step 4: AI-based Summarization**
def generate_summary(text):
    """Generate an unbiased AI summary using Hugging Face models."""
    summary = summarizer(text, max_length=150, min_length=50, do_sample=False)
    return summary[0]["summary_text"]

@api_view(["POST"])
@csrf_exempt
def analyze_news(request):
    """Main function to analyze news and determine legitimacy."""
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method"}, status=400)
    
    try:
        data = json.loads(request.body)
        news_text = data.get("news_text", "").strip()
        
        if not news_text:
            return JsonResponse({"error": "News text is required"}, status=400)
        
        # Step 1: Fetch news from APIs
        articles = fetch_news_google(news_text)

        # Step 2: Check if articles are from trusted sources
        trusted_articles = [article for article in articles if any(src in article["source"] for src in TRUSTED_SOURCES)]

        # Step 3: Scrape content & verify similarity
        final_articles = []
        for article in trusted_articles:
            scraped_content = scrape_article(article["url"])
            if scraped_content and is_similar(scraped_content, news_text):
                final_articles.append(article)

        # Step 4: Generate AI unbiased summary
        if final_articles:
            combined_text = " ".join([scrape_article(article["url"]) for article in final_articles if scrape_article(article["url"])])
            unbiased_summary = generate_summary(combined_text) if combined_text else "Summary not available"
            
            return JsonResponse({
                "status": "real",
                "message": "Verified news from trusted sources",
                "bias_score": 0,  # Assume trusted sources have low bias
                "unbiased_summary": unbiased_summary,
                "perspectives": final_articles
            })
        else:
            return JsonResponse({
                "status": "fake",
                "message": "No verified sources found",
                "bias_score": 100,
                "unbiased_summary": "N/A",
                "perspectives": []
            })
    
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON input"}, status=400)
