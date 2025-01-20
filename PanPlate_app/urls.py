from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from PanPlate_app import views

urlpatterns = [
    path('', views.MainPageView.as_view(), name='main'),
    path('profile/<int:user_id>/', views.ProfileView.as_view(), name='profile'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('video/<int:video_id>/save/', views.save_video, name='save_video'),
    path('video/<int:video_id>/like/', views.like_video, name='like_video'),
    path('video/<int:video_id>/', views.VideoDetailView.as_view(), name='video_detail'),  # Video detail page
    path('profile/change/<int:user_id>/', views.UpdateProfileView.as_view(), name='profile_change'),
    path('video/add/<int:user_id>/', views.AddVideoView.as_view(), name='add_video'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
