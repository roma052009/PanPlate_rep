from django.db import models
from django.contrib.auth.models import User

class Hashtag(models.Model):
    name = models.CharField(max_length=255)
    video = models.ForeignKey('Video', on_delete=models.CASCADE, related_name='hashtags')

    def __str__(self):
        return self.name

class Video(models.Model):
    creator = models.ForeignKey(User, on_delete=models.CASCADE, related_name='videos')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='videos/')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)  # Save the model first to ensure `self.file.path` is available

        # Generate and save the thumbnail if it doesn't exist
        if not self.thumbnail and self.file:
            try:
                output_path = os.path.join(settings.MEDIA_ROOT, 'thumbnails', f'{self.pk}_thumbnail.jpg')
                os.makedirs(os.path.dirname(output_path), exist_ok=True)  # Ensure directory exists

                # Use FFmpeg to extract the first frame
                ffmpeg.input(self.file.path, ss=1).output(output_path, vframes=1).run(overwrite_output=True)

                # Save the thumbnail
                self.thumbnail.name = f'thumbnails/{self.pk}_thumbnail.jpg'
                super().save(update_fields=['thumbnail'])  # Save only the updated thumbnail field
            except Exception as e:
                print(f"Error generating thumbnail: {e}")

class Recommendation(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='recommendations')
    hashtag = models.ForeignKey(Hashtag, on_delete=models.CASCADE, related_name='recommendations')
    score = models.PositiveIntegerField()

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.message

class Message(models.Model):
    chat = models.ForeignKey('Chat', on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

class Chat(models.Model):
    participants = models.ManyToManyField(User, related_name='chats')

    def __str__(self):
        return f"Chat between {', '.join([user.username for user in self.participants.all()])}"

class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='likes')

class View(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='views')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='views')

class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.text[:50]

class SavedVideo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_videos')
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='saved_by')

class Role(models.Model):
    name = models.CharField(max_length=50, unique=True)  
    description = models.TextField(blank=True, null=True)  

    def __str__(self):
        return self.name
    
class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='roles')  
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='users')  

    def __str__(self):
        return f"{self.user.username} - {self.role.name}"
