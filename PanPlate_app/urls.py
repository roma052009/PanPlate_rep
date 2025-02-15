from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from PanPlate_app import views

urlpatterns = [
    path('', views.MainPageView.as_view(), name='main'),
    path('profile/<int:user_id>/', views.ProfileView.as_view(), name='profile'),
    path('another_user_profile/<int:user_id>/', views.AnotherProfileView.as_view(), name='another_user_profile'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('video/<int:video_id>/save/', views.save_video, name='save_video'),
    path('video/<int:video_id>/like/', views.like_video, name='like_video'),
    path('video/<int:video_id>/', views.VideoDetailView.as_view(), name='video_detail'),  # Video detail page
    path('profile/change/<int:user_id>/', views.UpdateProfileView.as_view(), name='profile_change'),
    path('video/add/<int:user_id>/', views.AddVideoView.as_view(), name='add_video'),
    path('subscribe/<int:creator_id>/', views.subscribe, name='subscribe'),
    path('subscriptions/', views.SubscriptionListView.as_view(), name='subscriptions_list'),
    path('chats/', views.ChatListView.as_view(), name='chat_list'),
    path('chats/create/', views.ChatCreateView.as_view(), name='chat_create'),
    path('chats/<int:chat_id>/', views.ChatDetailView.as_view(), name='chat_detail'),
    path('groups/', views.GroupListView.as_view(), name='group_list'),
    path('groups/<int:group_id>/', views.GroupChatView.as_view(), name='group_chat'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
