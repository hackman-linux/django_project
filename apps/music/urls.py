from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.home,               name='home'),
    path('track/<uuid:track_id>/',        views.track_detail,       name='track_detail'),
    path('artist/<int:artist_id>/',       views.artist_page,        name='artist_page'),
    path('upload/',                       views.upload_track,       name='upload_track'),
    path('dashboard/',                    views.artist_dashboard,   name='artist_dashboard'),
    path('announcement/post/',            views.post_announcement,  name='post_announcement'),
]
