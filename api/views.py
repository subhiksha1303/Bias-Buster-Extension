import re
import requests
import json
import os
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
import nltk
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
from textblob import TextBlob  # For basic sentiment analysis

def home(request):
    return render(request, "index.html")

# List of trusted sources (Global + Indian)
TRUSTED_SOURCES = {
    "BBC", "CNN", "The Guardian", "Reuters", "The New York Times", "Al Jazeera", 
    "The Washington Post", "The Hindu", "The Indian Express", "Hindustan Times", 
    "NDTV", "Times of India", "Economic Times", "Deccan Herald", "Business Standard", 
    "The Quint", "India Today", "DNA India", "Scroll.in", "The Print", 
    "The Telegraph India", "Firstpost", "News18", "Financial Express"
}

def is_trusted_source(source_name):
    return source_name in TRUSTED_SOURCES

def calculate_bias_score(text):
    blob = TextBlob(text)
    polarity_score = (blob.sentiment.polarity + 1) * 50  # Convert to 0-100 scale

    BIAS_WORDS = {"leftist", "right-wing", "propaganda", "agenda", "liberal", "radical"}
    bias_count = sum(word in text.lower() for word in BIAS_WORDS)

    bias_score = round(polarity_score + (bias_count * 5), 2)  # Adjust bias score
    return min(bias_score, 100)  # Cap at 100

NEWS_API_KEY = os.getenv("NEWS_API_KEY")  # Store API key in environment variables
NEWS_API_URL = "https://newsapi.org/v2/everything"

def extract_keywords(text):
    words = re.findall(r'\b\w+\b', text)
    stopwords = {"the", "is", "in", "a", "an", "on", "of", "and", "to", "for", "with"}
    keywords = [word for word in words if word.lower() not in stopwords]
    return " ".join(keywords[:8])

def fetch_news_from_newsapi(query):
    params = {"q": query, "apiKey": NEWS_API_KEY, "language": "en", "sortBy": "relevancy"}
    response = requests.get(NEWS_API_URL, params=params)
    
    if response.status_code != 200:
        return {"status": "error", "message": "Failed to fetch news from NewsAPI."}
    
    return response.json().get("articles", [])

def analyze_sentiment(text):
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
    words = text.split()
    filtered_words = [word for word in words if word.lower() not in HARSH_WORDS]
    return " ".join(filtered_words)

def generate_objective_summary(text):
    cleaned_text = remove_harsh_words(text)
    sentences = re.split(r'(?<=[.!?]) +', cleaned_text)
    summary = " ".join(sentences[:5])  # Use the first 5 sentences as summary
    return summary

@api_view(["POST"])
@csrf_exempt
def analyze_news(request):
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
        trusted_source_found = False

        if articles:
            for article in articles[:5]:  
                source_name = article.get("source", {}).get("name", "Unknown")
                is_trusted = is_trusted_source(source_name)

                if is_trusted:
                    trusted_source_found = True

                perspectives.append({
                    "source": source_name,
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "sentiment": analyze_sentiment(article.get("content", ""))
                })

            # Generate an objective summary
            objective_summary = generate_objective_summary(news_text)
            
            # Calculate bias score
            bias_score = calculate_bias_score(news_text)

            return JsonResponse({
                "status": "real" if trusted_source_found else "fake",
                "bias_score": bias_score, 
                "objective_summary": objective_summary,
                "message": "News is verified. Here are different perspectives:",
                "perspectives": perspectives
            })
        
        return JsonResponse({"status": "fake", "message": "No reliable sources found."})
    
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON input."}, status=400)
