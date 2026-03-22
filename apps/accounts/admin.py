from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ArtistProfile, Subscription


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display  = ('username', 'email', 'user_type', 'is_premium', 'created_at')
    list_filter   = ('user_type', 'is_premium', 'is_active')
    search_fields = ('username', 'email')

    # Add our custom fields to the admin edit form
    fieldsets = UserAdmin.fieldsets + (
        ('NapsterLegal', {
            'fields': ('user_type', 'avatar', 'bio', 'is_premium', 'premium_until')
        }),
    )


@admin.register(ArtistProfile)
class ArtistProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'stage_name', 'country', 'verified', 'monthly_listeners')
    list_filter   = ('verified', 'country')
    search_fields = ('stage_name', 'user__username')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display  = ('user', 'status', 'started_at', 'expires_at', 'amount')
    list_filter   = ('status',)
    search_fields = ('user__username',)