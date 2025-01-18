from django.shortcuts import render, redirect
from django.views.generic import ListView, View
from PanPlate_app.models import Video, User, UserAvatar
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils.timezone import now
import random

class MainPageView(ListView):
    model = Video
    template_name = 'PanPlate_app/main_page.html'
    context_object_name = 'videos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        videos = Video.objects.all()
        if not videos.exists():
            context['video'] = None
            return context

        weights = []
        current_time = now()
        for video in videos:
            age_in_days = (current_time - video.created_at).days + 1
            weight = 1 / age_in_days
            weights.append(weight)

        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        selected_video = random.choices(videos, weights=normalized_weights, k=1)[0]
        context['video'] = selected_video
        return context

class ProfileView(LoginRequiredMixin, View):
    template_name = 'PanPlate_app/profile.html'

    def get(self, request, *args, **kwargs):
        try:
            avatar = UserAvatar.objects.get(user=request.user).avatar.url
            print(avatar)
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"  # Path to default avatar

        return render(request, self.template_name, {
            'user': request.user,
            'avatar': avatar,
        })


class LogoutView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        logout(request)
        return redirect('/')

class LoginView(View):
    template_name = 'PanPlate_app/login.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect('/')
        return render(request, self.template_name, {'error': 'Invalid credentials'})

class SignUpView(View):
    template_name = 'PanPlate_app/signup.html'

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name)

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        password_confirmation = request.POST.get('password_confirmation')
        email = request.POST.get('email')  # Getting the email input
        
        # Check if the password and confirmation match
        if password != password_confirmation:
            return render(request, self.template_name, {'error': 'Passwords do not match'})
        
        # Check if the username already exists
        if User.objects.filter(username=username).exists():
            return render(request, self.template_name, {'error': 'Username already exists'})
        
        # Check if the email is valid and not already in use
        if not email:
            return render(request, self.template_name, {'error': 'Email is required'})
        
        try:
            validate_email(email)  # Validate the email format
        except ValidationError:
            return render(request, self.template_name, {'error': 'Invalid email format'})
        
        if User.objects.filter(email=email).exists():
            return render(request, self.template_name, {'error': 'Email is already in use'})
        
        # Create the user
        user = User.objects.create_user(username=username, password=password, email=email)
        user.save()

        # Automatically log in the user after sign-up
        login(request, user)
        
        return redirect('/')