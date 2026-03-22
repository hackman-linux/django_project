from django.urls import path
from . import views

urlpatterns = [
    path('stream/<uuid:track_id>/', views.stream_track, name='stream_track'),
    path('track/<uuid:track_id>/info/', views.track_info, name='track_info'),
]
