# Generated by Django 5.1 on 2024-09-14 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('session_tracker', '0002_alter_usersession_site'),
    ]

    operations = [
        migrations.AlterField(
            model_name='site',
            name='domain',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
