from django.urls import path
from .views import analyze_news

urlpatterns = [
    path("analyze-news/", analyze_news, name="analyze_news"),
]
