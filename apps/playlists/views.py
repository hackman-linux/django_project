from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Playlist, PlaylistTrack
from apps.music.models import Track


@login_required
def playlist_list(request):
    playlists = request.user.playlists.all()
    return render(request, 'playlists/my_playlists.html', {'playlists': playlists})


@login_required
def create_playlist(request):
    if request.method == 'POST':
        name        = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        is_public   = request.POST.get('is_public') == 'on'

        if not name:
            messages.error(request, 'Playlist name is required.')
            return redirect('playlists')

        playlist = Playlist.objects.create(
            owner=request.user,
            name=name,
            description=description,
            is_public=is_public,
        )
        messages.success(request, f'Playlist "{name}" created!')
        return redirect('playlist_detail', pk=playlist.id)

    return redirect('playlists')


@login_required
def playlist_detail(request, pk):
    playlist = get_object_or_404(Playlist, id=pk)

    # Only owner or public playlists
    if not playlist.is_public and playlist.owner != request.user:
        messages.error(request, 'This playlist is private.')
        return redirect('playlists')

    tracks = PlaylistTrack.objects.filter(
        playlist=playlist
    ).select_related('track', 'track__artist').order_by('position')

    return render(request, 'playlists/playlist_detail.html', {
        'playlist': playlist,
        'tracks':   tracks,
    })


@login_required
def add_to_playlist(request, track_id):
    """Add a track to a playlist — called via POST."""
    if request.method == 'POST':
        playlist_id = request.POST.get('playlist_id')
        track       = get_object_or_404(Track, id=track_id)
        playlist    = get_object_or_404(Playlist, id=playlist_id, owner=request.user)

        # Get next position
        last = PlaylistTrack.objects.filter(playlist=playlist).order_by('-position').first()
        position = (last.position + 1) if last else 0

        PlaylistTrack.objects.get_or_create(
            playlist=playlist,
            track=track,
            defaults={'position': position, 'added_by': request.user}
        )
        messages.success(request, f'Added "{track.title}" to "{playlist.name}"')

        # Return JSON if AJAX, else redirect back
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'status': 'ok'})
        return redirect(request.META.get('HTTP_REFERER', 'home'))

    return redirect('home')


@login_required
def remove_from_playlist(request, playlist_id, track_id):
    playlist = get_object_or_404(Playlist, id=playlist_id, owner=request.user)
    PlaylistTrack.objects.filter(playlist=playlist, track_id=track_id).delete()
    messages.success(request, 'Track removed from playlist.')
    return redirect('playlist_detail', pk=playlist_id)


@login_required
def delete_playlist(request, pk):
    playlist = get_object_or_404(Playlist, id=pk, owner=request.user)
    name = playlist.name
    playlist.delete()
    messages.success(request, f'Playlist "{name}" deleted.')
    return redirect('playlists')
