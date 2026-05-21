from django.urls import path
from . import views

urlpatterns = [
    path('',                          views.pricing,       name='pricing'),
    path('subscribe/<str:plan_slug>/',views.subscribe,          name='subscribe'),
    path('success/<uuid:sub_id>/',    views.subscribe_success,name='subscription_success'),
    path('my-subscription/',          views.my_subscription,    name='my_subscription'),
    path('cancel/',                   views.cancel_subscription, name='cancel_subscription'),
]
