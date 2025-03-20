import re
import requests
import json
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from difflib import SequenceMatcher  # For text similarity checking
import nltk

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

try:
    nltk.data.find("tokenizers/punkt_tab")
except LookupError:
    nltk.download("punkt_tab")

# ✅ Home Page Function
def home(request):
    return render(request, "index.html")

# ✅ List of Trusted News Sources (Based on URL Domains)
TRUSTED_SOURCES = {
    "bbc.com", "cnn.com", "reuters.com", "theguardian.com", "nytimes.com",
    "aljazeera.com", "washingtonpost.com", "ndtv.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "business-standard.com", "news18.com",
    "thehindu.com", "firstpost.com", "scroll.in", "theprint.in"
}

# ✅ Function to Check if a News Source is Trusted
def is_trusted_source(url):
    return any(source in url for source in TRUSTED_SOURCES)

# ✅ Function to Fetch News Using Google Custom Search API
GOOGLE_API_KEY = "AIzaSyD0RJdZ3NtQAI9Y2KqSiTdcfK3a0ulMHf0"  # Replace with your actual key
GOOGLE_CSE_ID = "86f38c27f03df4661"  # Replace with your actual Custom Search Engine ID

def fetch_news_google(query):
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={GOOGLE_CSE_ID}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    return response.json().get("items", [])

# ✅ Function to Fetch News from NewsAPI
NEWS_API_KEY = "e242defe23904eee96b22acfb4d1ecee"  # Replace with your actual key
NEWS_API_URL = "https://newsapi.org/v2/everything"

def fetch_news_newsapi(query):
    params = {"q": query, "apiKey": NEWS_API_KEY, "language": "en", "pageSize": 5}
    response = requests.get(NEWS_API_URL, params=params)
    if response.status_code != 200:
        return []
    return response.json().get("articles", [])

# ✅ Function to Extract Keywords from Text
def extract_keywords(text):
    words = re.findall(r'\b\w+\b', text.lower())
    stopwords = {"the", "is", "in", "a", "an", "on", "of", "and", "to", "for", "with"}
    return " ".join([word for word in words if word not in stopwords][:8])

# ✅ Function to Check Similarity Between Two Texts
def text_similarity(text1, text2):
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

# ✅ Function to Generate an Unbiased Summary
def generate_summary(text):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LsaSummarizer()
    summary = summarizer(parser.document, 3)  # Generate a summary with 3 sentences
    return " ".join(str(sentence) for sentence in summary)

#✅ API Endpoint for News Analysis
@api_view(["POST"])
@csrf_exempt
def analyze_news(request):
    try:
        data = json.loads(request.body)
        news_text = data.get("news_text", "").strip()

        if not news_text:
            return JsonResponse({"status": "error", "message": "News text is required."}, status=400)

        keyword_query = extract_keywords(news_text)
        
        # Fetch news from both APIs
        google_news = fetch_news_google(keyword_query)
        newsapi_news = fetch_news_newsapi(keyword_query)

        all_articles = google_news + newsapi_news
        perspectives = []
        trusted_source_found = False

        if all_articles:
            for article in all_articles[:5]:  
                title = article.get("title", "")
                url = article.get("link", article.get("url", ""))
                source_name = article.get("displayLink", article.get("source", {}).get("name", "Unknown"))
                
                is_trusted = is_trusted_source(url)
                if is_trusted:
                    trusted_source_found = True
                
                # Check if the article is relevant
                similarity_score = text_similarity(news_text, title)
                if similarity_score < 0.5:  # Ignore unrelated articles
                    continue

                perspectives.append({
                    "source": source_name,
                    "title": title,
                    "url": url,
                })

            # Generate unbiased summary
            objective_summary = generate_summary(news_text)

            return JsonResponse({
                "status": "real" if trusted_source_found else "fake",
                "message": "News verified. Here are different perspectives:",
                "unbiased_summary": objective_summary,
                "perspectives": perspectives
            })
        
        return JsonResponse({"status": "fake", "message": "No reliable sources found."})
    
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON input."}, status=400)

