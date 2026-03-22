import uuid
from django.db import models
from apps.accounts.models import CustomUser
from apps.music.models import Track


class Playlist(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name            = models.CharField(max_length=200)
    owner           = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                        related_name='playlists')
    description     = models.TextField(blank=True)
    cover_image     = models.ImageField(upload_to='covers/', null=True, blank=True)
    is_public       = models.BooleanField(default=True)
    is_collaborative = models.BooleanField(default=False)
    tracks          = models.ManyToManyField(Track, through='PlaylistTrack',
                                             blank=True, related_name='playlists')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} by {self.owner.username}"

    def track_count(self):
        return self.tracks.count()

    class Meta:
        ordering = ['-created_at']


class PlaylistTrack(models.Model):
    playlist  = models.ForeignKey(Playlist, on_delete=models.CASCADE)
    track     = models.ForeignKey(Track, on_delete=models.CASCADE)
    position  = models.PositiveIntegerField(default=0)
    added_by  = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    added_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['position']
        unique_together = ('playlist', 'track')