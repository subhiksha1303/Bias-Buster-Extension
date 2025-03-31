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
from bs4 import BeautifulSoup

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

def dashboard(request):
    return render(request, 'home.html')  # Dashboard Page

def about(request):
    return render(request, 'about.html')

def extract_news_from_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        response = requests.get(url, headers=headers, timeout=5)
        
        if response.status_code != 200:
            return None, f"Error fetching URL: HTTP {response.status_code}"

        soup = BeautifulSoup(response.text, "html.parser")

        # Extract text from <p> tags inside article sections
        paragraphs = soup.find_all("p")
        article_text = " ".join([p.get_text() for p in paragraphs if len(p.get_text()) > 30])

        if not article_text:
            return None, "No readable content found in the article."

        return article_text.strip(), None
    except requests.exceptions.RequestException as e:
        return None, f"Request failed: {str(e)}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"
    
# ✅ List of Trusted News Sources (Based on URL Domains)
TRUSTED_SOURCES = {
    "bbc.com", "cnn.com", "reuters.com", "theguardian.com", "nytimes.com",
    "aljazeera.com", "washingtonpost.com", "ndtv.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "business-standard.com", "news18.com",
    "thehindu.com", "firstpost.com", "scroll.in", "theprint.in",  "nbcnews.com"
    "abcnews.go.com", "wsj.com", "apnews.com", "cbsnews.com", "foxnews.com",
    "usatoday.com", "latimes.com", "bloomberg.com", "politico.com", "bostonglobe.com"
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

import requests
from bs4 import BeautifulSoup

def fetch_other_perspectives(query):
    search_url = f"https://newsapi.org/v2/everything?q={query}&language=en&apiKey=YOUR_NEWSAPI_KEY"
    response = requests.get(search_url)
    articles = response.json().get("articles", [])
    
    other_perspectives = []
    
    for article in articles[:5]:  # Fetch up to 5 articles
        article_data = {
            "title": article.get("title", "No title available"),
            "published_at": article.get("publishedAt", "Unknown date"),
            "content": article.get("content", "No content available"),
            "source": article.get("source", {}).get("name", "Unknown source")
        }
        other_perspectives.append(article_data)
    
    return other_perspectives

def display_other_perspectives(other_perspectives):
    html_content = "<div class='other-perspectives'>"
    for article in other_perspectives:
        html_content += f"""
        <div class='perspective-box'>
            <h3>{article['title']}</h3>
            <p><strong>Source:</strong> {article['source']}</p>
            <p><strong>Published At:</strong> {article['published_at']}</p>
            <p>{article['content']}</p>
        </div>
        """
    html_content += "</div>"
    return html_content

# [Previous imports remain exactly the same...]

#✅ API Endpoint for News Analysis
@api_view(["POST","GET"])
@csrf_exempt
def analyze_news(request):
    try:
        data = json.loads(request.body)
        news_text = data.get("news_text", "").strip()
        news_url = data.get("news_url", "").strip()

        if news_url:
            extracted_text, error = extract_news_from_url(news_url)
            if error:
                return JsonResponse({"status": "error", "message": error}, status=400)
            news_text = extracted_text 

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
            for article in all_articles[:5]:  # Limit to 5 perspectives
                try:
                    title = article.get("title", "")
                    url = article.get("link", article.get("url", ""))
                    if not url:
                        continue
                        
                    source_name = article.get("displayLink", "") or \
                                article.get("source", {}).get("name", "Unknown")
                    
                    # Extract full article content
                    extracted_content, _ = extract_news_from_url(url)
                    if not extracted_content:
                        continue
                    
                    # Check relevance (lowered threshold to 0.3 for better matching)
                    similarity_score = text_similarity(news_text, title)
                    if similarity_score < 0.3:
                        continue

                    # Check if source is trusted
                    is_trusted = is_trusted_source(url)
                    if is_trusted:
                        trusted_source_found = True

                    perspectives.append({
                        "source": source_name,
                        "title": title,
                        "url": url,
                        "published_at": article.get("publishedAt", ""),
                        "content": extracted_content[:1000] + "..." if len(extracted_content) > 1000 else extracted_content
                    })
                    
                except Exception as e:
                    print(f"Error processing article: {str(e)}")
                    continue

            # Generate unbiased summary
            objective_summary = generate_summary(news_text)

            return JsonResponse({
                "status": "real" if trusted_source_found else "fake",
                "message": "Analysis complete",
                "unbiased_summary": objective_summary,
                "perspectives": perspectives
            })
        
        return JsonResponse({
            "status": "fake", 
            "message": "No related articles found.",
            "unbiased_summary": generate_summary(news_text),
            "perspectives": []
        })
    
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON input."}, status=400)
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Server error: {str(e)}"}, status=500)

