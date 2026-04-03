from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts import views as account_views

urlpatterns = [
    path('admin/',     admin.site.urls),
    path('',           include('apps.music.urls')),
    path('accounts/',  include('apps.accounts.urls')),
    path('profile/',   account_views.profile_view,  name='profile'),
    path('search/',    include('apps.search.urls')),
    path('playlists/', include('apps.playlists.urls')),
    path('social/',    include('apps.social.urls')),
    path('api/',       include('apps.api.urls')),
    path('pricing/',   include('apps.payments.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
