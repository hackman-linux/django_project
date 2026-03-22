from django.urls import path
from . import views

urlpatterns = [
    path('',                              views.playlist_list,       name='playlists'),
    path('create/',                       views.create_playlist,     name='create_playlist'),
    path('<uuid:pk>/',                    views.playlist_detail,     name='playlist_detail'),
    path('<uuid:pk>/delete/',             views.delete_playlist,     name='delete_playlist'),
    path('add/<uuid:track_id>/',          views.add_to_playlist,     name='add_to_playlist'),
    path('<uuid:playlist_id>/remove/<uuid:track_id>/',
                                          views.remove_from_playlist,name='remove_from_playlist'),
]
