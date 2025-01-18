from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, View
from PanPlate_app.models import Hashtag, Video, Recommendation, Notification, Message, Chat, Like, View, Comment, SavedVideo, Role, UserRole
from django.contrib.auth.models import User
from django.utils.timezone import now
import random


class MainPageView(ListView):
    model = Video
    template_name = 'PanPlate_app/main_page.html'
    context_object_name = 'videos'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all videos and calculate weights based on creation date
        videos = Video.objects.all()
        if not videos.exists():
            context['video'] = None  # Handle case with no videos
            return context

        # Calculate weights: Newer videos get higher weights
        weights = []
        current_time = now()
        for video in videos:
            age_in_days = (current_time - video.created_at).days + 1  # Add 1 to avoid division by zero
            weight = 1 / age_in_days  # Older videos get smaller weight
            weights.append(weight)
        
        # Normalize weights so they sum to 1
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Choose a random video using weights
        selected_video = random.choices(videos, weights=normalized_weights, k=1)[0]
        
        context['video'] = selected_video
        return context