from django.urls import path
from . import views

urlpatterns = [
    path('login/',                           views.admin_login,       name='cp_login'),
    path('logout/',                          views.admin_logout,      name='cp_logout'),
    path('',                                 views.dashboard,         name='cp_dashboard'),
    path('users/',                           views.users_list,        name='cp_users'),
    path('users/create/',                    views.create_staff,      name='cp_create_staff'),
    path('users/<uuid:user_id>/toggle/',     views.toggle_user,       name='cp_toggle_user'),
    path('tracks/',                          views.tracks_list,       name='cp_tracks'),
    path('tracks/<uuid:track_id>/toggle/',   views.toggle_track,      name='cp_toggle_track'),
    path('artists/',                         views.artists_list,      name='cp_artists'),
    path('artists/<int:artist_id>/verify/',  views.verify_artist,     name='cp_verify_artist'),
    path('analytics/',                       views.analytics_view,    name='cp_analytics'),
    path('logs/',                            views.logs_view,         name='cp_logs'),
    path('messages/',                        views.messages_view,     name='cp_messages'),
    path('messages/<int:msg_id>/',           views.message_detail,    name='cp_message_detail'),
    path('settings/',                        views.app_settings,      name='cp_settings'),
    path('my-space/',                        views.admin_my_space,    name='cp_my_space'),
]
