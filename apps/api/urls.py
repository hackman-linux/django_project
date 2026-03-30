from django.urls import path
from apps.music import views as music_views
from . import views

urlpatterns = [
    path('stream/<uuid:track_id>/',      views.stream_track,           name='stream_track'),
    path('track/<uuid:track_id>/info/',  views.track_info,             name='track_info'),
    path('log-listen/',                  views.log_listen,             name='log_listen'),
    # Lyrics detection — called from upload.html and edit_track.html via Alpine.js fetch
    path('detect-lyrics/',               music_views.detect_lyrics,    name='detect_lyrics'),
]