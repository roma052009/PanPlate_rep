from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.generic import ListView, DetailView, View
from PanPlate_app.models import Video, User, UserAvatar, View_for_video, Comment, SavedVideo, Like, Subscription, Chat, Message, GroupMember
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
    
class AnotherProfileView(View):
    template_name = 'PanPlate_app/another_user_profile.html'

    def get(self, request, user_id, *args, **kwargs):
        user = get_object_or_404(User, id=user_id)
        try:
            own_avatar = UserAvatar.objects.get(user=self.request.user).avatar.url
        except:
            own_avatar = "/media/avatars/no_image.jpg"

        # Get avatar or default
        try:
            avatar = UserAvatar.objects.get(user=user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"

        # Fetch user's uploaded videos
        user_videos = Video.objects.filter(creator=user)

        # Check subscription status safely
        subscribed = False
        if request.user.is_authenticated:
            subscribed = Subscription.objects.filter(user=request.user, subscribed_to=user).exists()

        return render(request, self.template_name, {
            'profile_user': user,
            'profile_user_avatar': avatar,
            'avatar': own_avatar,
            'user_videos': user_videos,
            'subscribed': subscribed,
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

@login_required
def subscribe(request, creator_id):
    user = request.user
    creator = get_object_or_404(User, id=creator_id)

    subscription, created = Subscription.objects.get_or_create(user=user, subscribed_to=creator)

    if not created:
        subscription.delete()  # Delete the specific instance if already subscribed

    return redirect('another_user_profile', user_id=creator_id)

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
        
class SubscriptionListView(LoginRequiredMixin, ListView):
    model = Subscription
    template_name = 'PanPlate_app/subscriptions.html'
    context_object_name = 'subscriptions'

    def get_queryset(self):
        # Only return subscriptions for the logged-in user
        return Subscription.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        # Get the default context
        context = super().get_context_data(**kwargs)
        
        # Get the user's avatar (assuming the model has a OneToOneField for User)
        try:
            avatar = UserAvatar.objects.get(user=self.request.user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"

        # Add avatar to context
        context['avatar'] = avatar
        
        return context

class ChatListView(LoginRequiredMixin, View):
    def get(self, request):
        chats = Chat.objects.filter(participants=request.user)
        
        # Fetch user avatar
        try:
            avatar = UserAvatar.objects.get(user=request.user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"
        
        return render(request, 'PanPlate_app/chat_list.html', {'chats': chats, 'avatar': avatar})

class ChatCreateView(LoginRequiredMixin, View):
    def get(self, request):
        user = request.user

        # Find users who are mutually subscribed
        mutual_subscribers = User.objects.filter(
            id__in=Subscription.objects.filter(user=user).values_list('subscribed_to', flat=True)
        ).filter(
            id__in=Subscription.objects.filter(subscribed_to=user).values_list('user', flat=True)
        )

        # Fetch user avatar
        try:
            avatar = UserAvatar.objects.get(user=user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"

        return render(request, 'PanPlate_app/chat_create.html', {'users': mutual_subscribers, 'avatar': avatar})

    def post(self, request):
        user_ids = request.POST.getlist('participants')  # Get selected users

        if not user_ids:
            return redirect('chat_list')  # If no user is selected, go back

        chat = Chat.objects.create()
        chat.participants.add(request.user, *User.objects.filter(id__in=user_ids))
        return redirect('chat_list')

class ChatDetailView(LoginRequiredMixin, View):
    def get(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
        messages = chat.messages.order_by('created_at')  # Oldest messages first

        # Fetch user avatar
        try:
            avatar = UserAvatar.objects.get(user=request.user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"

        return render(request, 'PanPlate_app/chat_detail.html', {'chat': chat, 'messages': messages, 'avatar': avatar})

    def post(self, request, chat_id):
        chat = get_object_or_404(Chat, id=chat_id, participants=request.user)
        text = request.POST.get('message')

        if text.strip():  # Prevent empty messages
            Message.objects.create(chat=chat, sender=request.user, text=text)

        return redirect('chat_detail', chat_id=chat.id)

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views import View
from .models import Group, GroupMessage

class GroupListView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            avatar = UserAvatar.objects.get(user=request.user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"
        groups = Group.objects.filter(memberships__user=request.user)
        return render(request, 'PanPlate_app/group_list.html', {'groups': groups, 'avatar': avatar})

class GroupChatView(LoginRequiredMixin, View):
    def get(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)
        messages = group.messages.all()
        try:
            avatar = UserAvatar.objects.get(user=request.user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"
        return render(request, 'PanPlate_app/group_chat.html', {
            'group': group,
            'messages': messages,
            'avatar': avatar
        })

    def post(self, request, group_id):
        group = get_object_or_404(Group, id=group_id)

        if group.owner == request.user:
            content = request.POST.get("content", "").strip()
            if content:
                GroupMessage.objects.create(group=group, sender=request.user, content=content)

        return redirect('group_chat', group_id=group.id)

class SearchResultsView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        try:
            avatar = UserAvatar.objects.get(user=request.user).avatar.url
        except UserAvatar.DoesNotExist:
            avatar = "/media/avatars/no_image.jpg"
        groups = Group.objects.filter(memberships__user=request.user)

        videos = Video.objects.filter(title__icontains=query) if query else []
        people = User.objects.filter(username__icontains=query) if query else []
        groups = Group.objects.filter(name__icontains=query) if query else []

        return render(request, 'PanPlate_app/search_results.html', {
            'query': query,
            'videos': videos,
            'people': people,
            'groups': groups,
            'avatar': avatar,
        })
    
class GroupDetailView(DetailView):
    model = Group
    template_name = 'PanPlate_app/group_detail.html'
    context_object_name = 'group'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        group = context['group']

        # Check if the user is a member of the group
        is_member = GroupMember.objects.filter(group=group, user=self.request.user).exists()

        # Add is_member and is_subscribed to the context
        context['is_member'] = is_member
        context['is_subscribed'] = is_member  # Assuming subscription status is tied to group membership

        return context


@login_required
def toggle_subscription(request, group_id):
    group = get_object_or_404(Group, id=group_id)
    user = request.user

    # Try to get the GroupMember entry; if it doesn't exist, create one
    membership, created = GroupMember.objects.get_or_create(group=group, user=user)

    if not created:
        membership.delete()  # If the user is already a member, unsubscribe by deleting

    return redirect('group-detail', pk=group.id)