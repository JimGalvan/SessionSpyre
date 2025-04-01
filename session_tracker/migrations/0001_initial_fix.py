from django.db import migrations, connection
from django.utils import timezone


def create_initial_tables(apps, schema_editor):
    """
    Creates the initial tables needed for the application to function.
    This migration runs before any other migrations to ensure the tables exist.
    """
    with connection.cursor() as cursor:
        # Create the UserAccount table first
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS "session_tracker_useraccount" (
                "password" varchar(128) NOT NULL,
                "last_login" timestamp with time zone NULL,
                "is_superuser" boolean NOT NULL,
                "username" varchar(150) NOT NULL UNIQUE,
                "first_name" varchar(150) NOT NULL,
                "last_name" varchar(150) NOT NULL,
                "email" varchar(254) NOT NULL,
                "is_staff" boolean NOT NULL,
                "is_active" boolean NOT NULL,
                "date_joined" timestamp with time zone NOT NULL,
                "id" uuid NOT NULL PRIMARY KEY
            );
        """)

        # Create the django_migrations table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS django_migrations (
                id serial PRIMARY KEY,
                app VARCHAR(255) NOT NULL,
                name VARCHAR(255) NOT NULL,
                applied TIMESTAMP WITH TIME ZONE NOT NULL
            );
        """)

        # Record this migration
        now = timezone.now().isoformat()
        cursor.execute("""
            INSERT INTO django_migrations (app, name, applied)
            VALUES (%s, %s, %s)
            ON CONFLICT (app, name) DO NOTHING
        """, ['session_tracker', '0001_initial_fix', now])


def reverse_migration(apps, schema_editor):
    """
    No need to do anything on reverse - we don't want to drop tables.
    """
    pass


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('session_tracker', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_initial_tables, reverse_migration),
    ] 