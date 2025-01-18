from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from PanPlate_app import views

urlpatterns = [
    path('', views.MainPageView.as_view(), name='main'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('signup/', views.SignUpView.as_view(), name='signup'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
