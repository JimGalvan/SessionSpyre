from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Sets up initial tables required for migrations to run'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self.stdout.write('Creating initial tables...')
            
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
            self.stdout.write(self.style.SUCCESS('Successfully created session_tracker_useraccount table')) 