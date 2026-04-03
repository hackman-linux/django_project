import uuid
from django.db import models
from apps.accounts.models import CustomUser, ArtistProfile


class Genre(models.Model):
    name      = models.CharField(max_length=50, unique=True)
    slug      = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    color_hex = models.CharField(max_length=7, default='#6366F1')

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class Album(models.Model):
    SINGLE = 'single'
    EP     = 'ep'
    ALBUM  = 'album'
    TYPE_CHOICES = [
        (SINGLE, 'Single'),
        (EP,     'EP'),
        (ALBUM,  'Album'),
    ]

    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title        = models.CharField(max_length=200)
    artist       = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE,
                                     related_name='albums')
    cover_image  = models.ImageField(upload_to='covers/', null=True, blank=True)
    release_date = models.DateField(null=True, blank=True)
    album_type   = models.CharField(max_length=10, choices=TYPE_CHOICES, default=SINGLE)
    description  = models.TextField(blank=True)
    is_published = models.BooleanField(default=False)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.artist}"

    class Meta:
        ordering = ['-release_date']


class Track(models.Model):
    CC_BY      = 'cc_by'
    CC_BY_NC   = 'cc_by_nc'
    ALL_RIGHTS = 'all_rights'
    LICENSE_CHOICES = [
        (CC_BY,      'Creative Commons BY'),
        (CC_BY_NC,   'Creative Commons BY-NC'),
        (ALL_RIGHTS, 'All Rights Reserved'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title         = models.CharField(max_length=200)
    artist        = models.ForeignKey(ArtistProfile, on_delete=models.CASCADE,
                                      related_name='tracks')
    album         = models.ForeignKey(Album, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='tracks')
    genre         = models.ForeignKey(Genre, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='tracks')
    audio_file    = models.FileField(upload_to='tracks/')
    cover_image   = models.ImageField(upload_to='covers/', null=True, blank=True)
    duration      = models.PositiveIntegerField(default=0, help_text='Duration in seconds')
    lyrics        = models.TextField(blank=True)
    is_explicit   = models.BooleanField(default=False)
    license_type  = models.CharField(max_length=20, choices=LICENSE_CHOICES,
                                     default=ALL_RIGHTS)
    bpm           = models.PositiveIntegerField(null=True, blank=True)
    play_count    = models.PositiveIntegerField(default=0)
    like_count    = models.PositiveIntegerField(default=0)
    waveform_data = models.JSONField(default=list, blank=True)
    tags          = models.ManyToManyField('Tag', blank=True, related_name='tracks')
    preview_start = models.PositiveIntegerField(default=0,
                                                help_text='Preview start in seconds')
    # AcoustID fingerprinting fields
    acoustid_checked = models.BooleanField(default=False,
        help_text='Whether AcoustID fingerprint check has been run')
    acoustid_result  = models.JSONField(default=dict, blank=True,
        help_text='Raw AcoustID API response — admin only')
    acoustid_status  = models.CharField(
        max_length=20, default='pending',
        help_text='pending / passed / failed / error')

    # AcoustID fingerprinting fields
    acoustid_checked = models.BooleanField(default=False,
        help_text='Whether AcoustID fingerprint check has been run')
    acoustid_result  = models.JSONField(default=dict, blank=True,
        help_text='Raw AcoustID API response — admin only')
    acoustid_status  = models.CharField(
        max_length=20, default='pending',
        help_text='pending / passed / failed / error')

    is_published  = models.BooleanField(default=False)
    uploaded_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} — {self.artist}"

    def duration_display(self):
        mins = self.duration // 60
        secs = self.duration % 60
        return f"{mins}:{secs:02d}"

    class Meta:
        ordering = ['-uploaded_at']


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name

class Announcement(models.Model):
    """
    Artists can post announcements directly to their followers.
    Shown on the artist page — direct fan relationship.
    """
    artist     = models.ForeignKey(
        ArtistProfile, on_delete=models.CASCADE, related_name='announcements')
    title      = models.CharField(max_length=200)
    body       = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_pinned  = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.artist.stage_name} — {self.title}"

    class Meta:
        ordering = ['-is_pinned', '-created_at']


class AnnouncementLike(models.Model):
    user         = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.CASCADE,
        related_name='announcement_likes')
    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name='likes')
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'announcement')


class AnnouncementComment(models.Model):
    user         = models.ForeignKey(
        'accounts.CustomUser', on_delete=models.CASCADE,
        related_name='announcement_comments')
    announcement = models.ForeignKey(
        Announcement, on_delete=models.CASCADE, related_name='comments')
    body         = models.TextField()
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
