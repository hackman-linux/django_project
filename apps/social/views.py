from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from apps.music.models import Track
from .models import Like, Follow, Comment
from apps.accounts.models import ArtistProfile


@login_required
def like_toggle(request, track_id):
    track = get_object_or_404(Track, id=track_id)
    like, created = Like.objects.get_or_create(user=request.user, track=track)
    if not created:
        like.delete()
        track.like_count = max(0, track.like_count - 1)
        liked = False
    else:
        track.like_count += 1
        liked = True
    track.save(update_fields=['like_count'])
    return JsonResponse({'liked': liked, 'like_count': track.like_count})


@login_required
def follow_toggle(request, artist_id):
    artist = get_object_or_404(ArtistProfile, id=artist_id)
    follow, created = Follow.objects.get_or_create(
        follower=request.user, following=artist)
    if not created:
        follow.delete()
        followed = False
    else:
        followed = True
    return JsonResponse({'followed': followed})


@login_required
@require_POST
def add_comment(request, track_id):
    track   = get_object_or_404(Track, id=track_id)
    content = request.POST.get('content', '').strip()
    if content:
        Comment.objects.create(user=request.user, track=track, content=content)
    return redirect('track_detail', track_id=track_id)
