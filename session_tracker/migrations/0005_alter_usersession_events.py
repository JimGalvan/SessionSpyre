# Generated by Django 5.1 on 2024-09-26 06:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('session_tracker', '0004_alter_usersession_events'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersession',
            name='events',
            field=models.JSONField(),
        ),
    ]
