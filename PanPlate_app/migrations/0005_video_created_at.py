# Generated by Django 5.1.4 on 2025-01-15 22:18

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('PanPlate_app', '0004_remove_video_watched'),
    ]

    operations = [
        migrations.AddField(
            model_name='video',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
