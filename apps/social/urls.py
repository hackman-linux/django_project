from django.urls import path
from . import views

urlpatterns = [
    path('like/<uuid:track_id>/',    views.like_toggle,   name='like_toggle'),
    path('follow/<int:artist_id>/',  views.follow_toggle, name='follow_toggle'),
    path('comment/<uuid:track_id>/', views.add_comment,   name='add_comment'),
]
