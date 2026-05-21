from django.urls import path
from . import views

urlpatterns = [
    path('stream/<uuid:track_id>/',     views.stream_track,  name='stream_track'),
    path('track/<uuid:track_id>/info/', views.track_info,    name='track_info'),
    path('log-listen/',                 views.log_listen,    name='log_listen'),
    path('download/<uuid:track_id>/',   views.download_track,name='download_track'),
    path('my-downloads/',               views.my_downloads,  name='my_downloads'),
    path('detect-lyrics/',              views.detect_lyrics, name='detect_lyrics'),
]
