from django.contrib import admin
from .models import Playlist, PlaylistTrack


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display  = ('name', 'owner', 'is_public', 'is_collaborative',
                     'track_count', 'created_at')
    list_filter   = ('is_public', 'is_collaborative')
    search_fields = ('name', 'owner__username')


@admin.register(PlaylistTrack)
class PlaylistTrackAdmin(admin.ModelAdmin):
    list_display = ('playlist', 'track', 'position', 'added_by', 'added_at')