from django.shortcuts import render
from apps.music.models import Track, Genre
from apps.accounts.models import ArtistProfile


def _log_search(request, query, results_count):
    """Log the search query to MariaDB."""
    try:
        from apps.analytics.models import SearchLog
        SearchLog.objects.using('analytics').create(
            query=query,
            user_id=request.user.id if request.user.is_authenticated else None,
            results_count=results_count,
        )
    except Exception as e:
        print(f"Search log error: {e}")


def search_view(request):
    query  = request.GET.get('q', '').strip()
    genre  = request.GET.get('genre', '')
    sort   = request.GET.get('sort', 'relevance')

    tracks  = Track.objects.filter(is_published=True).select_related('artist', 'genre')
    artists = ArtistProfile.objects.all()
    genres  = Genre.objects.all()

    if query:
        tracks  = tracks.filter(title__icontains=query)
        artists = artists.filter(stage_name__icontains=query)

    if genre:
        tracks = tracks.filter(genre__slug=genre)

    if sort == 'popular':
        tracks = tracks.order_by('-play_count')
    elif sort == 'new':
        tracks = tracks.order_by('-uploaded_at')
    elif sort == 'liked':
        tracks = tracks.order_by('-like_count')
    else:
        tracks = tracks.order_by('-play_count')

    tracks  = tracks[:24]
    artists = artists[:8]

    # Log to MariaDB if there was a query
    if query:
        _log_search(request, query, tracks.count())

    return render(request, 'search/results.html', {
        'query':         query,
        'tracks':        tracks,
        'artists':       artists,
        'genres':        genres,
        'current_genre': genre,
        'current_sort':  sort,
    })
