# Generated by Django 5.1.5 on 2025-02-18 20:11

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0026_rename_timestamp_notification_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='assigned_date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
