from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, RoyaltyPool, ArtistRoyalty

@admin.register(SubscriptionPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price_monthly', 'price_yearly', 'is_active')

@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'billing_cycle', 'amount_paid', 'expires_at')
    list_filter  = ('status', 'plan', 'billing_cycle')

@admin.register(RoyaltyPool)
class RoyaltyPoolAdmin(admin.ModelAdmin):
    list_display = ('month', 'total_revenue', 'artist_pool', 'platform_cut',
                    'total_streams', 'distributed')

@admin.register(ArtistRoyalty)
class ArtistRoyaltyAdmin(admin.ModelAdmin):
    list_display = ('artist', 'pool', 'streams', 'stream_share', 'amount', 'paid')
