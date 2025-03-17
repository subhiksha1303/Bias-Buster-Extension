import re
import requests
import json
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.decorators import api_view
from django.views.decorators.csrf import csrf_exempt
from textblob import TextBlob  # For basic sentiment analysis

def home(request):
    return render(request, "index.html")

def calculate_bias_score(text):
    blob = TextBlob(text)
    polarity = blob.sentiment.polarity  # Range: -1 (negative) to 1 (positive)
    
    # Convert polarity to a 0-100 scale
    bias_score = round((polarity + 1) * 50, 2)
    return bias_score

NEWS_API_KEY = "e242defe23904eee96b22acfb4d1ecee"
NEWS_API_URL = "https://newsapi.org/v2/everything"

def extract_keywords(text):
    words = re.findall(r'\b\w+\b', text)
    stopwords = {"the", "is", "in", "a", "an", "on", "of", "and", "to", "for", "with"}
    keywords = [word for word in words if word.lower() not in stopwords]
    return " ".join(keywords[:8])


def fetch_news_from_newsapi(query):
    params = {
        "q": query,
        "apiKey": NEWS_API_KEY,
        "language": "en",
        "sortBy": "relevancy"
    }
    
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
    # Remove harsh words
    cleaned_text = remove_harsh_words(text)
    # Use the first 3 sentences as a simple summary
    sentences = re.split(r'(?<=[.!?]) +', cleaned_text)
    summary = " ".join(sentences[:5])
    
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
        
        if articles:
            perspectives = []
            for article in articles[:5]:  
                content = article.get("content", "")
                sentiment = analyze_sentiment(content)
                perspectives.append({
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "title": article.get("title", ""),
                    "url": article.get("url", ""),
                    "sentiment": sentiment
                })
            
            # Generate an objective summary
            objective_summary = generate_objective_summary(news_text)
            
            # Calculate bias score
            bias_score = calculate_bias_score(news_text)

            return JsonResponse({
                "status": "real",
                "bias_score": bias_score, 
                "objective_summary": objective_summary,
                "message": "News is verified. Here are different perspectives:",
                "perspectives": perspectives
            })
        
        return JsonResponse({"status": "fake", "message": "No reliable sources found."})
    
    except json.JSONDecodeError:
        return JsonResponse({"status": "error", "message": "Invalid JSON input."}, status=400)