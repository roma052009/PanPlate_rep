from django.contrib import admin
from PanPlate_app.models import Hashtag, Video, Recommendation, Notification, Message, Chat, Like, View_for_video, Comment, SavedVideo, Role, UserRole, UserAvatar, Subscription, Group, GroupMember, GroupMessage


admin.site.register(Hashtag)
admin.site.register(Video)
admin.site.register(Recommendation)
admin.site.register(Notification)
admin.site.register(Message)
admin.site.register(Chat)
admin.site.register(Like)
admin.site.register(View_for_video)
admin.site.register(Comment)
admin.site.register(SavedVideo)
admin.site.register(UserAvatar)
admin.site.register(Subscription)
admin.site.register(Group)
admin.site.register(GroupMember)
admin.site.register(GroupMessage)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')