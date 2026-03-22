from django.db import models


class PlayEvent(models.Model):
    """Every time a track is played — stored in MariaDB."""
    track_id          = models.UUIDField()
    user_id           = models.UUIDField(null=True, blank=True)
    session_id        = models.CharField(max_length=100, blank=True)
    listened_duration = models.PositiveIntegerField(default=0)
    completed         = models.BooleanField(default=False)
    ip_address        = models.GenericIPAddressField(null=True, blank=True)
    country_code      = models.CharField(max_length=2, blank=True)
    device_type       = models.CharField(max_length=50, blank=True)
    timestamp         = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'analytics'
        ordering  = ['-timestamp']

    def __str__(self):
        return f"Play {self.track_id} at {self.timestamp}"


class SearchLog(models.Model):
    """Every search query — stored in MariaDB."""
    query            = models.CharField(max_length=200)
    user_id          = models.UUIDField(null=True, blank=True)
    results_count    = models.PositiveIntegerField(default=0)
    clicked_track_id = models.UUIDField(null=True, blank=True)
    timestamp        = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        app_label = 'analytics'
        ordering  = ['-timestamp']

    def __str__(self):
        return f"Search: {self.query}"


class ArtistStats(models.Model):
    """Daily stats per artist — stored in MariaDB."""
    artist_id        = models.UUIDField(db_index=True)
    date             = models.DateField(db_index=True)
    total_plays      = models.PositiveIntegerField(default=0)
    unique_listeners = models.PositiveIntegerField(default=0)
    new_followers    = models.PositiveIntegerField(default=0)
    top_track_id     = models.UUIDField(null=True, blank=True)
    revenue_estimate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        app_label = 'analytics'
        unique_together = ('artist_id', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"Stats for {self.artist_id} on {self.date}"