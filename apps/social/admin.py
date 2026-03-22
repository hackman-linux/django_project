from django.contrib import admin
from .models import Follow, Like, Comment


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ('user', 'track', 'created_at')

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display  = ('user', 'track', 'created_at', 'parent')
    search_fields = ('content', 'user__username')