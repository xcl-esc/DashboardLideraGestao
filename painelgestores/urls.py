from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path
from usuarios import views

urlpatterns = [
    path("admin/", admin.site.urls),

    path("", lambda request: redirect("login")),

    path("login/", views.login_view, name="login"),
    path("cadastro/", views.cadastro_view, name="cadastro"),
    path("home/", views.HomeView.as_view(), name="home"), 
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("desempenho/", views.desempenho_view, name="desempenho"),
    path("panorama/", views.panorama_view, name="panorama"),
    path("extracoes/", views.extracoes, name="extracoes"),
]

