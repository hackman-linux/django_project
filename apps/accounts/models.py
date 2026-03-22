import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    """
    Our main user model. Extends Django's built-in user
    and adds fields for the NapsterLegal platform.
    """

    # User type choices
    LISTENER = 'listener'
    ARTIST   = 'artist'
    ADMIN    = 'admin'

    USER_TYPE_CHOICES = [
        (LISTENER, 'Listener'),
        (ARTIST,   'Artist'),
        (ADMIN,    'Admin'),
    ]

    # Extra fields
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type   = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default=LISTENER)
    avatar      = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio         = models.TextField(blank=True)
    is_premium  = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.user_type})"

    def is_artist(self):
        return self.user_type == self.ARTIST

    def is_listener(self):
        return self.user_type == self.LISTENER

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class ArtistProfile(models.Model):
    """
    Extended profile for users who are artists.
    Created automatically when user_type is set to 'artist'.
    """
    user             = models.OneToOneField(CustomUser, on_delete=models.CASCADE,
                                            related_name='artist_profile')
    stage_name       = models.CharField(max_length=100, blank=True)
    country          = models.CharField(max_length=100, blank=True)
    monthly_listeners = models.PositiveIntegerField(default=0)
    verified         = models.BooleanField(default=False)
    social_links     = models.JSONField(default=dict, blank=True)
    # genres will be added as M2M after Genre model is created in music app

    def __str__(self):
        return f"{self.stage_name or self.user.username} (Artist)"

    class Meta:
        verbose_name = 'Artist Profile'
        verbose_name_plural = 'Artist Profiles'


class Subscription(models.Model):
    """
    Tracks premium subscription history for users.
    """
    ACTIVE    = 'active'
    EXPIRED   = 'expired'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (ACTIVE,    'Active'),
        (EXPIRED,   'Expired'),
        (CANCELLED, 'Cancelled'),
    ]

    user       = models.ForeignKey(CustomUser, on_delete=models.CASCADE,
                                   related_name='subscriptions')
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    amount     = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} — {self.status}"

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-started_at']