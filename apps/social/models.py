from django.db import models
from apps.accounts.models import CustomUser, ArtistProfile
from apps.music.models import Track


class Follow(models.Model):
    follower  = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                  related_name='following')
    following = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE,
                                  related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.follower.username} follows {self.following}"


class Like(models.Model):
    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                   related_name='likes')
    track      = models.ForeignKey(Track, on_delete=models.CASCADE,
                                   related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'track')

    def __str__(self):
        return f"{self.user.username} likes {self.track.title}"


class Comment(models.Model):
    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                   related_name='comments')
    track      = models.ForeignKey(Track, on_delete=models.CASCADE,
                                   related_name='comments')
    content    = models.TextField()
    parent     = models.ForeignKey('self', on_delete=models.CASCADE,
                                   null=True, blank=True, related_name='replies')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} on {self.track.title}"