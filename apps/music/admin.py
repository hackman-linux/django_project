from django.contrib import admin
from .models import Genre, Album, Track, Tag


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display  = ('name', 'slug', 'color_hex')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display  = ('title', 'artist', 'album_type', 'is_published', 'release_date')
    list_filter   = ('album_type', 'is_published')
    search_fields = ('title', 'artist__stage_name')


@admin.register(Track)
class TrackAdmin(admin.ModelAdmin):
    list_display  = ('title', 'artist', 'genre', 'duration_display',
                     'play_count', 'is_published')
    list_filter   = ('genre', 'is_published', 'is_explicit', 'license_type')
    search_fields = ('title', 'artist__stage_name')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}