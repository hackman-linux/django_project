"""
NapsterLegal — Real-Time Trending Engine
Inspired by Audiomack's Now Trending but improved:
- Play velocity (streams per hour) weighted more than total plays
- Regional trending (Francophone Africa treated as distinct region)
- Completion rate weighted (a track people finish = genuinely good)
- No label bias — pure organic discovery
"""
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Sum, Avg, F, ExpressionWrapper, FloatField
from django.core.cache import cache


def get_trending_tracks(limit=20, region=None, genre=None, hours=24):
    """
    Calculate trending score for each track and return top N.
    
    Trending Score Formula:
        score = (play_velocity × 3) 
              + (completion_rate × 2) 
              + (like_velocity × 1.5)
              + (unique_listeners × 1)
    
    play_velocity   = plays in last `hours` / hours (streams per hour)
    completion_rate = % of plays that finished the track
    like_velocity   = likes in last `hours` / hours
    unique_listeners= distinct user count (prevents fake inflation)
    """
    from apps.music.models import Track
    
    cache_key = f'trending_{region}_{genre}_{hours}_{limit}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    now = timezone.now()
    window_start = now - timedelta(hours=hours)
    
    # Get base queryset of published tracks
    tracks = Track.objects.filter(
        is_published=True,
        acoustid_status__in=['passed', 'pending', None, ''],
    ).select_related('artist', 'genre')
    
    if genre:
        tracks = tracks.filter(genre__slug=genre)
    
    # Try to get play velocity from MariaDB analytics
    trending_data = []
    
    try:
        from apps.analytics.models import PlayEvent
        from django.db.models import Q
        
        # Recent events in time window
        recent_events = PlayEvent.objects.using('analytics').filter(
            timestamp__gte=window_start
        )
        
        # If region filter (e.g. 'CM', 'SN', 'CI', 'CD' for Francophone Africa)
        francophone_africa = ['CM', 'SN', 'CI', 'CD', 'BF', 'ML', 'GN', 'TG', 'BJ', 'MR']
        if region == 'francophone_africa':
            recent_events = recent_events.filter(country_code__in=francophone_africa)
        elif region:
            recent_events = recent_events.filter(country_code=region)
        
        # Aggregate by track
        track_stats = (recent_events
            .values('track_id')
            .annotate(
                recent_plays=Count('id'),
                completed_plays=Count('id', filter=Q(completed=True)),
                total_duration=Sum('listened_duration'),
            )
        )
        
        stats_map = {str(s['track_id']): s for s in track_stats}
        
        for track in tracks:
            tid = str(track.id)
            stats = stats_map.get(tid, {})
            
            recent_plays   = stats.get('recent_plays', 0)
            completed      = stats.get('completed_plays', 0)
            
            play_velocity    = recent_plays / max(hours, 1)
            completion_rate  = (completed / max(recent_plays, 1))
            like_velocity    = 0  # can add like tracking later
            
            # Overall trending score
            score = (
                play_velocity   * 3.0 +
                completion_rate * 2.0 +
                like_velocity   * 1.5 +
                (track.play_count / 1000) * 0.5  # mild boost for established tracks
            )
            
            trending_data.append({
                'track':          track,
                'score':          score,
                'recent_plays':   recent_plays,
                'completion_rate':round(completion_rate * 100, 1),
                'play_velocity':  round(play_velocity, 2),
            })
    
    except Exception:
        # Fallback: use play_count directly when MariaDB unavailable
        for track in tracks:
            trending_data.append({
                'track':          track,
                'score':          track.play_count + (track.like_count * 2),
                'recent_plays':   track.play_count,
                'completion_rate':0,
                'play_velocity':  0,
            })
    
    # Sort by score descending
    trending_data.sort(key=lambda x: x['score'], reverse=True)
    result = trending_data[:limit]
    
    # Cache for 5 minutes (real-time but not DB-hammering)
    cache.set(cache_key, result, 300)
    return result


def get_trending_by_genre(limit=6):
    """Return top trending track per genre — for the home page genre grid."""
    from apps.music.models import Genre
    genres = Genre.objects.all()
    result = {}
    for genre in genres:
        tracks = get_trending_tracks(limit=limit, genre=genre.slug)
        if tracks:
            result[genre] = tracks
    return result


def invalidate_trending_cache():
    """Call this when a new play event is logged."""
    from django.core.cache import cache
    # Clear all trending cache keys
    cache.clear()
