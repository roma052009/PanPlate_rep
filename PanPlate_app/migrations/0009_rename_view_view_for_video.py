# Generated by Django 5.1.4 on 2025-01-19 13:30

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('PanPlate_app', '0008_subscription'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(
            old_name='View',
            new_name='View_for_video',
        ),
    ]
