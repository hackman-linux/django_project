from django.urls import path
from . import views

urlpatterns = [
    path('',                                views.home,             name='home'),
    path('track/<uuid:track_id>/',          views.track_detail,     name='track_detail'),
    path('track/<uuid:track_id>/edit/',     views.edit_track,       name='edit_track'),
    path('track/<uuid:track_id>/delete/',   views.delete_track,     name='delete_track'),
    path('artist/<int:artist_id>/',         views.artist_page,      name='artist_page'),
    path('upload/',                         views.upload_track,     name='upload_track'),
    path('dashboard/',                      views.artist_dashboard, name='artist_dashboard'),
]
