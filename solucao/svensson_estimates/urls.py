from django.urls import path
from . import views

app_name = 'svensson_estimates'

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('api/attempts/', views.list_attempts, name='list_attempts'),
    path('api/attempts/previous-best/', views.best_previous_attempt, name='best_previous_attempt'),
    path('api/attempts/create/', views.create_attempt, name='create_attempt'),
    path('api/attempts/<int:attempt_id>/update/', views.update_attempt, name='update_attempt'),
    path('api/attempts/<int:attempt_id>/delete/', views.delete_attempt, name='delete_attempt'),
    path('api/attempts/<int:attempt_id>/curve/', views.get_svensson_curve, name='get_svensson_curve'),
    path('api/attempts/<int:attempt_id>/improve/', views.improve_attempt, name='improve_attempt'),
]

