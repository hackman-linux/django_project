import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    LISTENER = 'listener'
    ARTIST   = 'artist'
    ADMIN    = 'admin'

    USER_TYPE_CHOICES = [
        (LISTENER, 'Listener'),
        (ARTIST,   'Artist'),
        (ADMIN,    'Admin'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_type     = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default=LISTENER)
    avatar        = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio           = models.TextField(blank=True)
    is_premium    = models.BooleanField(default=False)
    premium_until = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.username} ({self.user_type})"

    def is_artist(self):
        return self.user_type == self.ARTIST

    def is_listener(self):
        return self.user_type == self.LISTENER

    class Meta:
        verbose_name        = 'User'
        verbose_name_plural = 'Users'


class ArtistProfile(models.Model):
    # Verification status choices
    PENDING  = 'pending'
    VERIFIED = 'verified'
    REJECTED = 'rejected'

    VERIFICATION_CHOICES = [
        (PENDING,  'Pending Review'),
        (VERIFIED, 'Verified'),
        (REJECTED, 'Rejected'),
    ]

    # Basic profile
    user              = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='artist_profile')
    stage_name        = models.CharField(max_length=100, blank=True)
    country           = models.CharField(max_length=100, blank=True)
    monthly_listeners = models.PositiveIntegerField(default=0)
    verified          = models.BooleanField(default=False)
    social_links      = models.JSONField(default=dict, blank=True)

    # Verification system fields
    verification_status   = models.CharField(
        max_length=10, choices=VERIFICATION_CHOICES, default=PENDING)
    real_name             = models.CharField(
        max_length=200, blank=True,
        help_text='Legal full name — kept private, admin only')
    id_document           = models.FileField(
        upload_to='verification/ids/', null=True, blank=True,
        help_text='Government ID or passport — stored securely, admin only')
    existing_work_url     = models.URLField(
        blank=True,
        help_text='Link to your music on YouTube, SoundCloud, Instagram, etc.')
    verification_note     = models.TextField(
        blank=True,
        help_text='Admin note explaining verification decision')
    verification_date     = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.stage_name or self.user.username} (Artist)"

    def is_verified(self):
        return self.verification_status == self.VERIFIED

    def is_pending(self):
        return self.verification_status == self.PENDING

    class Meta:
        verbose_name        = 'Artist Profile'
        verbose_name_plural = 'Artist Profiles'


class Subscription(models.Model):
    ACTIVE    = 'active'
    EXPIRED   = 'expired'
    CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (ACTIVE,    'Active'),
        (EXPIRED,   'Expired'),
        (CANCELLED, 'Cancelled'),
    ]

    user       = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, related_name='subscriptions')
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default=ACTIVE)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    amount     = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.user.username} — {self.status}"

    class Meta:
        ordering = ['-started_at']


class ContactMessage(models.Model):
    """
    Messages sent by users to the admin via the Contact page.
    Visible in the admin control panel at /control/messages/.
    """
    OPEN     = 'open'
    REPLIED  = 'replied'
    CLOSED   = 'closed'

    STATUS_CHOICES = [
        (OPEN,    'Open'),
        (REPLIED, 'Replied'),
        (CLOSED,  'Closed'),
    ]

    sender     = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='sent_messages', null=True, blank=True)
    name       = models.CharField(max_length=100)
    email      = models.EmailField()
    subject    = models.CharField(max_length=200)
    body       = models.TextField()
    status     = models.CharField(max_length=10, choices=STATUS_CHOICES, default=OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    replied_at = models.DateTimeField(null=True, blank=True)
    reply_body = models.TextField(blank=True)

    def __str__(self):
        return f"{self.subject} — {self.name} ({self.status})"

    class Meta:
        ordering = ['-created_at']


class Notification(models.Model):
    """
    In-app notifications for users.
    Covers:
      - Admin replies to contact messages
      - Artist announcements to followers
      - Follower/like events for artists
      - System alerts
    """
    TYPE_ADMIN_REPLY    = 'admin_reply'
    TYPE_ARTIST_POST    = 'artist_post'
    TYPE_NEW_FOLLOWER   = 'new_follower'
    TYPE_TRACK_LIKED    = 'track_liked'
    TYPE_TRACK_APPROVED = 'track_approved'
    TYPE_TRACK_REJECTED = 'track_rejected'
    TYPE_SYSTEM         = 'system'

    TYPE_CHOICES = [
        (TYPE_ADMIN_REPLY,    'Admin Reply'),
        (TYPE_ARTIST_POST,    'Artist Announcement'),
        (TYPE_NEW_FOLLOWER,   'New Follower'),
        (TYPE_TRACK_LIKED,    'Track Liked'),
        (TYPE_TRACK_APPROVED, 'Track Approved'),
        (TYPE_TRACK_REJECTED, 'Track Rejected'),
        (TYPE_SYSTEM,         'System'),
    ]

    recipient   = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='notifications')
    notif_type  = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title       = models.CharField(max_length=200)
    body        = models.TextField()
    link        = models.CharField(max_length=300, blank=True)
    is_read     = models.BooleanField(default=False)
    created_at  = models.DateTimeField(auto_now_add=True)

    # Optional references
    sender_name = models.CharField(max_length=100, blank=True)
    extra_data  = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering  = ['-created_at']
        indexes   = [models.Index(fields=['recipient', 'is_read'])]

    def __str__(self):
        return f"→ {self.recipient.username}: {self.title}"

    @classmethod
    def send(cls, recipient, notif_type, title, body, link='', sender_name='', extra=None):
        """Create a notification and optionally send email."""
        notif = cls.objects.create(
            recipient   = recipient,
            notif_type  = notif_type,
            title       = title,
            body        = body,
            link        = link,
            sender_name = sender_name,
            extra_data  = extra or {},
        )
        # Send email notification
        try:
            from django.core.mail import send_mail
            from django.conf import settings
            send_mail(
                subject      = f'[NapsterLegal] {title}',
                message      = f'{body}\n\n→ {settings.SITE_URL if hasattr(settings,"SITE_URL") else "http://localhost:8000"}{link}',
                from_email   = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@napsterlegal.com'),
                recipient_list=[recipient.email],
                fail_silently= True,
            )
        except Exception:
            pass
        return notif
