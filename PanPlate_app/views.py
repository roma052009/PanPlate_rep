from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, View
from PanPlate_app.models import Video, User, UserAvatar, View_for_video, Comment, SavedVideo, Like
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from .forms import CommentForm
from django.utils.timezone import now
import random
from django.db.models import Q

class MainPageView(View):
    def get(self, request, *args, **kwargs):
        user = request.user
        videos = list(Video.objects.all())  # Convert queryset to a list for easier handling

        # Fetch avatar for the user if authenticated
        avatar_path = "/media/avatars/no_image.jpg"
        if user.is_authenticated:
            try:
                avatar_path = UserAvatar.objects.get(user=user).avatar.url
            except UserAvatar.DoesNotExist:
                pass

        # Retrieve navigation action (up or down)
        action = request.GET.get("action")

        # Retrieve video history from session
        video_history = request.session.get("video_history", [])
        current_index = request.session.get("current_index", -1)

        if action == "up" and current_index > 0:
            # Move to the previous video in the history list
            current_index -= 1
            selected_video_id = video_history[current_index]

        elif action == "down":
            if current_index < len(video_history) - 1:
                # Move to the next video in the history list
                current_index += 1
                selected_video_id = video_history[current_index]
            else:
                # Choose a new random video and add it to history
                watched_video_ids = View_for_video.objects.filter(user=user).values_list('video_id', flat=True) if user.is_authenticated else []
                unwatched_videos = [v for v in videos if v.id not in watched_video_ids]

                # Pick from unwatched videos if available, otherwise from all videos
                videos_to_choose_from = unwatched_videos if unwatched_videos else videos

                # Weighted selection
                current_time = now()
                weights = [1 / ((current_time - v.created_at).days + 1) for v in videos_to_choose_from]
                selected_video = random.choices(videos_to_choose_from, weights=weights, k=1)[0]
                selected_video_id = selected_video.id

                # Update history list
                video_history.append(selected_video_id)
                current_index += 1

        else:
            # First-time visit or no action → Choose a new random video
            watched_video_ids = View_for_video.objects.filter(user=user).values_list('video_id', flat=True) if user.is_authenticated else []
            unwatched_videos = [v for v in videos if v.id not in watched_video_ids]
            videos_to_choose_from = unwatched_videos if unwatched_videos else videos

            # Weighted selection
            current_time = now()
            weights = [1 / ((current_time - v.created_at).days + 1) for v in videos_to_choose_from]
            selected_video = random.choices(videos_to_choose_from, weights=weights, k=1)[0]
            selected_video_id = selected_video.id

            # Start new history
            video_history = [selected_video_id]
            current_index = 0

        # Save history back to session
        request.session["video_history"] = video_history
        request.session["current_index"] = current_index
        request.session.modified = True

        return redirect("video_detail", video_id=selected_video_id)



class VideoDetailView(DetailView):
    model = Video
    template_name = 'PanPlate_app/video_detail.html'
    context_object_name = 'video'

    def get_object(self, queryset=None):
        # Get the video by the ID from the URL
        video_id = self.kwargs.get('video_id')
        return Video.objects.get(id=video_id)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        video = self.get_object()  # Get the video object

        def format_count(count):
            if count >= 1_000_000:
                return f"{count / 1_000_000:.1f}M"
            elif count >= 1_000:
                return f"{count / 1_000:.1f}K"
            return str(count)

        context['likes_count'] = format_count(video.likes.count())
        context['saves_count'] = format_count(video.saved_by.count())
        context['comments_count'] = format_count(video.comments.count())

        try:
            context['creator_avatar'] = video.creator.useravatar.avatar.url
        except UserAvatar.DoesNotExist:
            context['creator_avatar'] = "/media/avatars/no_image.jpg"
        except AttributeError:
            context['creator_avatar'] = "/media/avatars/no_image.jpg"

        # Add comments for the video to the context
        comments = Comment.objects.filter(video=video)
        comments_with_avatars = []

        for comment in comments:
            avatar_path = (
                comment.user.useravatar.avatar.url
                if hasattr(comment.user, 'useravatar') and comment.user.useravatar.avatar
                else '/media/avatars/no_image.jpg'
            )
            comments_with_avatars.append({
                'comment': comment,
                'avatar': avatar_path,
            })

        context['comments_with_avatars'] = comments_with_avatars

        # Fetch avatar for the user if authenticated
        user = self.request.user
        context['user'] = user
        if user.is_authenticated:
            # Create a view record if it doesn't exist
            View_for_video.objects.get_or_create(user=user, video=video)
        if user.is_authenticated:
            try:
                context['avatar'] = UserAvatar.objects.get(user=user).avatar.url
            except UserAvatar.DoesNotExist:
                context['avatar'] = "/media/avatars/no_image.jpg"
            
            # Add liked and saved status to context
            context['liked'] = Like.objects.filter(user=user, video=video).exists()
            context['saved'] = SavedVideo.objects.filter(user=user, video=video).exists()
        else:
            context['avatar'] = "/media/avatars/no_image.jpg"
            context['liked'] = False
            context['saved'] = False

        return context

    def post(self, request, *args, **kwargs):
        video_id = self.kwargs.get('video_id')
        comment_text = request.POST.get('comment_text')

        if comment_text:
            video = Video.objects.get(id=video_id)
            user = request.user

            # Save the comment
            Comment.objects.create(user=user, video=video, text=comment_text)

        # Redirect to the same video detail page to display the new comment
        return redirect('video_detail', video_id=video_id)



class ProfileView(LoginRequiredMixin, View):
    template_name = 'PanPlate_app/profile.html'

    def get(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id)

        # Get avatar or default
        try:
            avatar = UserAvatar.objects.get(user=user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"

        # Fetch user's uploaded, liked, and saved videos
        user_videos = Video.objects.filter(creator=user)
        liked_videos = Like.objects.filter(user=user).select_related('video')
        saved_videos = SavedVideo.objects.filter(user=user).select_related('video')

        return render(request, self.template_name, {
            'user': user,
            'avatar': avatar,
            'user_videos': user_videos,
            'liked_videos': liked_videos,
            'saved_videos': saved_videos,
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

@login_required
def save_video(request, video_id):
    user = request.user
    video = Video.objects.get(id=video_id)
    if user.is_authenticated:
        # Check if the video is already saved
        saved_video, created = SavedVideo.objects.get_or_create(user=user, video_id=video_id)
        if not created:
            # If already saved, delete the save
            saved_video.delete()
    
    View_for_video.objects.get_or_create(user=user, video=video)

    return redirect('video_detail', video_id=video_id)  # Redirect to the video detail page

@login_required
def like_video(request, video_id):
    user = request.user
    if user.is_authenticated:
        # Check if the user already liked the video
        like, created = Like.objects.get_or_create(user=user, video_id=video_id)
        if not created:
            # If already liked, delete the like
            like.delete()

    return redirect('video_detail', video_id=video_id)  # Redirect to the video detail page

class UpdateProfileView(View):
    template_name = 'PanPlate_app/profile_change.html'

    def get(self, request, user_id, *args, **kwargs):
        # Get the user by user_id or return 404 if not found
        user = get_object_or_404(User, id=user_id)

        # Retrieve the avatar if it exists
        avatar = user.useravatar.avatar.url if hasattr(user, 'useravatar') else "/media/avatars/no_image.jpg"

        return render(request, self.template_name, {'user': user, 'avatar': avatar})

    def post(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id)

        # Update username and email
        username = request.POST.get('username')
        email = request.POST.get('email')

        try:
            # Ensure the username is unique
            if User.objects.filter(username=username).exists() and user.username != username:
                raise ValidationError("Username already exists.")

            user.username = username
            user.email = email

            # Update avatar if a new one is uploaded
            if request.FILES.get('avatar'):
                avatar = request.FILES['avatar']
                if not hasattr(user, 'useravatar'):
                    user.useravatar = UserAvatar(user=user)
                user.useravatar.avatar = avatar
                user.useravatar.save()

            user.save()

            return redirect('profile', user_id=user.id)

        except ValidationError as e:
            return render(request, self.template_name, {'user': user, 'error': str(e)})
        
class AddVideoView(View):
    template_name = 'PanPlate_app/add_video.html'

    def get(self, request, user_id, *args, **kwargs):
        # Get the user by user_id or return 404 if not found
        user = get_object_or_404(User, id=user_id)
        return render(request, self.template_name, {'user': user})

    def post(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id)

        # Get form data
        title = request.POST.get('title')
        file = request.FILES.get('file')
        thumbnail = request.FILES.get('thumbnail')

        if title and file:
            video = Video.objects.create(
                title=title,
                creator=user,
                file=file,
                thumbnail=thumbnail,
            )
            return redirect('video_detail', video_id=video.id)
        else:
            return render(request, self.template_name, {
                'error': 'All fields are required.',
                'user': user
            })