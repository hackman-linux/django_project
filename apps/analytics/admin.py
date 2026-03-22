from django.contrib import admin
from .models import PlayEvent, SearchLog, ArtistStats


@admin.register(PlayEvent)
class PlayEventAdmin(admin.ModelAdmin):
    list_display = ('track_id', 'user_id', 'listened_duration', 'completed', 'timestamp')
    list_filter  = ('completed', 'device_type')

@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ('query', 'user_id', 'results_count', 'timestamp')

@admin.register(ArtistStats)
class ArtistStatsAdmin(admin.ModelAdmin):
    list_display = ('artist_id', 'date', 'total_plays', 'unique_listeners', 'revenue_estimate')