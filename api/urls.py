from django.urls import path
from .views import analyze_news, home, dashboard, about, startpage

urlpatterns = [
    path("", home, name="home"),   
    path("analyze-news/", analyze_news, name="analyze_news"),  
    path('dashboard/', dashboard, name="dashboard"),
    path('about/', about, name="about"),
    path('startpage/', startpage, name="startpage"), 
]
