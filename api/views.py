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
from difflib import SequenceMatcher
import nltk
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from datetime import datetime

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

def clean_news_content(content):
    """Clean up news content to remove unwanted patterns and formatting"""
    if not content:
        return content
    
    # Remove timeline entries and date fragments
    content = re.sub(r'[A-Z][a-z]+\. \d+\.', '', content)  # "Feb. 14."
    content = re.sub(r'[A-Z][a-z]+ \d+:', '', content)     # "February 14:"
    content = re.sub(r'\d+ days? ago', '', content)        # "7 days ago"
    content = re.sub(r'\.\.\.', '.', content)             # Remove ellipses
    
    # Remove common non-article text
    unwanted_phrases = [
        'continue reading', 'read more', 'sign up', 'subscribe',
        'related coverage', 'more on this story', 'updated on',
        'published:', 'last updated', 'photo:', 'credit:'
    ]
    
    for phrase in unwanted_phrases:
        content = re.sub(phrase, '', content, flags=re.IGNORECASE)
    
    # Normalize whitespace and remove short fragments
    content = re.sub(r'\s+', ' ', content).strip()
    sentences = [s.strip() for s in content.split('.') if len(s.strip()) > 30]
    return '. '.join(sentences).strip()

def extract_news_from_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title = None
        title_selectors = [
            'meta[property="og:title"]',
            'meta[name="twitter:title"]',
            'h1',
            'title'
        ]
        
        for selector in title_selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get('content', '').strip() if hasattr(element, 'get') else element.get_text().strip()
                if title:
                    break
        
        # Clean up title
        if title:
            title = re.sub(r' - [^-]+$', '', title)
            title = re.sub(r'\s+', ' ', title).strip()
        
        # Extract publication date
        pub_date = None
        date_selectors = [
            'meta[property="article:published_time"]',
            'meta[name="date"]',
            'meta[name="publish-date"]',
            'meta[name="pubdate"]',
            'time[datetime]',
            'span.date',
            'div.timestamp',
            'p.published',
            'div.article-date'
        ]
        
        for selector in date_selectors:
            element = soup.select_one(selector)
            if element:
                pub_date = element.get('content') or element.get('datetime') or element.get_text()
                if pub_date:
                    pub_date = re.sub(r'[^\w\s:-]', '', pub_date.strip())
                    break
        
        # Parse date into standard format
        if pub_date:
            try:
                for fmt in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d %B %Y', '%b %d, %Y'):
                    try:
                        parsed_date = datetime.strptime(pub_date, fmt)
                        pub_date = parsed_date.strftime('%Y-%m-%d %H:%M:%S')
                        break
                    except ValueError:
                        continue
            except Exception:
                pub_date = None
        
        # Extract and clean content
        content_selectors = [
            'article',
            'main',
            'div.article',
            'div.content',
            'div.post',
            'div.story',
            'div.entry-content'
        ]
        
        content = None
        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                for tag in element(['script', 'style', 'nav', 'footer', 'aside', 'figure', 'iframe']):
                    tag.decompose()
                content = element.get_text(separator='\n', strip=True)
                if len(content) > 300:
                    break
        
        if not content or len(content) < 300:
            paragraphs = soup.find_all('p')
            content = '\n'.join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50)
        
        if content:
            content = clean_news_content(content)
            content = re.sub(r'\n{3,}', '\n\n', content).strip()
        
        if not title:
            title = "No title found"
        if not content:
            return None, None, None, "Could not extract meaningful content from the URL"
        
        return title, content, pub_date, None
        
    except Exception as e:
        return None, None, None, f"Error processing URL: {str(e)}"
    
# ✅ List of Trusted News Sources (Based on URL Domains)
TRUSTED_SOURCES = {
    "bbc.com", "cnn.com", "reuters.com", "theguardian.com", "nytimes.com",
    "aljazeera.com", "washingtonpost.com", "ndtv.com", "indiatoday.in",
    "timesofindia.indiatimes.com", "business-standard.com", "news18.com",
    "thehindu.com", "firstpost.com", "scroll.in", "theprint.in",  "nbcnews.com",
    "abcnews.go.com", "wsj.com", "apnews.com", "cbsnews.com", "foxnews.com",
    "usatoday.com", "latimes.com", "bloomberg.com", "politico.com", "bostonglobe.com",
    "indianexpress.com", "hindustantimes.com"
}

# ✅ Function to Check if a News Source is Trusted
def is_trusted_source(url):
    try:
        domain = urlparse(url).netloc.replace("www.", "")
        return any(domain.endswith(source) for source in TRUSTED_SOURCES)
    except Exception:
        return False

# ✅ Function to Fetch News Using Google Custom Search API
GOOGLE_API_KEY = "AIzaSyD0RJdZ3NtQAI9Y2KqSiTdcfK3a0ulMHf0"  # Replace with your actual key
GOOGLE_CSE_ID = "86f38c27f03df4661"  # Replace with your actual Custom Search Engine ID

def fetch_news_google(query):
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&cx={GOOGLE_CSE_ID}&key={GOOGLE_API_KEY}"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    results = response.json().get("items", [])
    return [article for article in results if is_trusted_source(article.get("link", ""))]

# ✅ Function to Fetch News from NewsAPI
NEWS_API_KEY = "e242defe23904eee96b22acfb4d1ecee"  # Replace with your actual key
NEWS_API_URL = "https://newsapi.org/v2/everything"

def fetch_news_newsapi(query):
    params = {"q": query, "apiKey": NEWS_API_KEY, "language": "en", "pageSize": 5}
    response = requests.get(NEWS_API_URL, params=params)
    if response.status_code != 200:
        return []
    articles = response.json().get("articles", [])
    return [article for article in articles if is_trusted_source(article.get("url", ""))]

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
    summary = summarizer(parser.document, 5)
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
        
        title = ""
        extracted_text = ""
        published_date = None
        is_trusted = False
        error = None

        if news_url:
            title, extracted_text, published_date, error = extract_news_from_url(news_url)
            if error or not extracted_text:
                return JsonResponse({"status": "error", "message": error or "Could not extract news content."}, status=400)
            
            news_text = extracted_text
            keyword_query = title if title else extract_keywords(news_text)
            is_trusted = is_trusted_source(news_url)
        else:
            if not news_text:
                return JsonResponse({"status": "error", "message": "News text is required."}, status=400)
            
            title = extract_keywords(news_text)
            keyword_query = title
            extracted_text = news_text
            published_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        google_news = fetch_news_google(keyword_query)
        newsapi_news = fetch_news_newsapi(keyword_query)

        all_articles = google_news + newsapi_news
        perspectives = []
        trusted_source_found = is_trusted

        for article in all_articles[:5]:
            try:
                article_title = article.get("title", "")
                article_url = article.get("link", article.get("url", ""))
                
                if not article_url or any(word in article_title.lower() for word in ['opinion', 'editorial', 'analysis', 'timeline']):
                    continue
                    
                if news_url:
                    _, perspective_content, perspective_pub_date, _= extract_news_from_url(article_url)
                    if not perspective_content or len(perspective_content) < 200:
                        continue
                    
                    title_similarity = text_similarity(title, article_title) if title else 0
                    content_similarity = text_similarity(extracted_text, perspective_content)
                    combined_similarity = max(title_similarity, content_similarity * 0.8)
                else:
                    perspective_content = article.get("description", article.get("snippet", ""))
                    combined_similarity = text_similarity(title, article_title)
                
                if combined_similarity < 0.3 or not perspective_content:
                    continue
                
                clean_content = clean_news_content(perspective_content)
                unbiased_version = generate_summary(clean_content) if clean_content else "No content available"
                
                perspective_trusted = is_trusted_source(article_url)
                trusted_source_found = trusted_source_found or perspective_trusted
                pub_date = (perspective_pub_date if news_url else 
                   article.get("publishedAt", "") or 
                   article.get("pubDate", "") or 
                   datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

                perspectives.append({
                    "source": article.get("source", {}).get("name", urlparse(article_url).netloc),
                    "title": article_title,
                    "url": article_url,
                    "published_at": pub_date,
                    "content": clean_content[:1000] + "..." if len(clean_content) > 1000 else clean_content,
                    "unbiased_version": unbiased_version,
                    "bias_score": round(combined_similarity * 100, 2),
                    "is_trusted": perspective_trusted
                })
                
            except Exception as e:
                print(f"Error processing perspective article: {str(e)}")
                continue

        objective_summary = generate_summary(extracted_text)

        return JsonResponse({
            "status": "real" if trusted_source_found else "fake",
            "message": "Analysis complete",
            "original_title": title if title else "No title extracted",
            "published_date": published_date if published_date else "Date not available",
            "unbiased_summary": objective_summary,
            "perspectives": perspectives,
            "legitimacy_score": 85 if trusted_source_found else 35,
            "source_trusted": is_trusted,
            "input_type": "url" if news_url else "text"
        })
    
    except Exception as e:
        return JsonResponse({"status": "error", "message": f"Server error: {str(e)}"}, status=500)