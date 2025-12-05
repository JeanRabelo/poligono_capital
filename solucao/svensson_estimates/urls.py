from django.urls import path
from . import views

app_name = 'svensson_estimates'

urlpatterns = [
    path('', views.homepage, name='homepage'),
]

