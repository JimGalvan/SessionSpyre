# Generated by Django 5.1 on 2024-09-26 05:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('session_tracker', '0003_alter_site_domain'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usersession',
            name='events',
            field=models.JSONField(default=list),
        ),
    ]
