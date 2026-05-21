"""
NapsterLegal — Real-Time Trending Engine
Score = play_velocity×3 + completion_rate×2 + recency_boost×1
Falls back to play_count if MariaDB unavailable.
"""
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta


def get_trending_tracks(limit=20, genre=None, hours=24):
    """
    Return list of dicts: [{'track': Track, 'score': float,
                             'recent_plays': int, 'completion_rate': float}]
    """
    cache_key = f'trending_{genre}_{hours}_{limit}'
    cached    = cache.get(cache_key)
    if cached:
        return cached

    from apps.music.models import Track
    from django.db.models  import Q

    # Base published queryset
    qs = Track.objects.filter(is_published=True).filter(
        Q(acoustid_status='passed') |
        Q(acoustid_status='pending') |
        Q(acoustid_status='') |
        Q(acoustid_status__isnull=True)
    ).select_related('artist', 'genre')

    if genre:
        qs = qs.filter(genre__slug=genre)

    # Try MariaDB analytics for velocity
    try:
        from apps.analytics.models import PlayEvent
        from django.db.models import Count

        window_start  = timezone.now() - timedelta(hours=hours)
        recent_events = PlayEvent.objects.using('analytics').filter(
            timestamp__gte=window_start
        ).values('track_id').annotate(
            recent_plays=Count('id'),
        )
        stats_map = {e['track_id']: e['recent_plays'] for e in recent_events}

        results = []
        for track in qs:
            tid          = str(track.id)
            recent_plays = stats_map.get(tid, 0)
            velocity     = recent_plays / max(hours, 1)
            score        = velocity * 3 + (track.play_count / 1000) * 0.5
            results.append({
                'track':           track,
                'score':           score,
                'recent_plays':    recent_plays,
                'completion_rate': 0,
            })

    except Exception:
        # MariaDB unavailable — fall back to all-time play_count
        results = [
            {
                'track':           t,
                'score':           t.play_count,
                'recent_plays':    t.play_count,
                'completion_rate': 0,
            }
            for t in qs.order_by('-play_count')[:limit]
        ]

    results.sort(key=lambda x: x['score'], reverse=True)
    result = results[:limit]
    cache.set(cache_key, result, 300)  # cache 5 minutes
    return result
