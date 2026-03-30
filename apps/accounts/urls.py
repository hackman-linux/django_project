from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('register/',     views.register_view,       name='register'),
    path('login/',        views.login_view,           name='login'),
    path('logout/',       views.logout_view,          name='logout'),
    # Profile
    path('profile/',      views.profile_view,         name='profile'),
    path('profile/edit/', views.profile_edit,         name='profile_edit'),
    # Custom admin
    path('manage/',                          views.admin_dashboard,     name='admin_dashboard'),
    path('manage/users/',                    views.admin_users,         name='admin_users'),
    path('manage/tracks/',                   views.admin_tracks,        name='admin_tracks'),
    path('manage/artists/',                  views.admin_artists,       name='admin_artists'),
    path('manage/artists/<int:artist_id>/verify/',
                                             views.admin_verify_artist, name='admin_verify_artist'),
    path('manage/users/<uuid:user_id>/toggle/',
                                             views.admin_toggle_user,   name='admin_toggle_user'),
    path('manage/tracks/<uuid:track_id>/toggle/',
                                             views.admin_toggle_track,  name='admin_toggle_track'),
]
