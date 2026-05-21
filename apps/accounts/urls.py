from django.urls import path
from . import views

urlpatterns = [
    path('register/',            views.register_view,         name='register'),
    path('login/',               views.login_view,            name='login'),
    path('logout/',              views.logout_view,           name='logout'),
    path('profile/',             views.profile_view,          name='profile'),
    path('profile/edit/',        views.profile_edit,          name='profile_edit'),
    path('settings/',            views.settings_view,         name='settings'),
    path('notifications/count/', views.notification_count,  name='notification_count'),
    path('notifications/',       views.notifications_view,  name='notifications'),
    path('contact/',             views.contact_view,          name='contact'),
    path('dashboard/listener/',  views.listener_dashboard,    name='listener_dashboard'),
    path('dashboard/artist/',    views.artist_home_dashboard, name='artist_home_dashboard'),
]
