from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps


class Command(BaseCommand):
    help = 'Generate SQL to fix migration issues in production'

    def handle(self, *args, **options):
        self.stdout.write('Starting migration fix process...')
        
        try:
            # Check if the UserAccount table exists
            table_exists = self.check_table_exists('session_tracker_useraccount')
            if table_exists:
                self.stdout.write('UserAccount table already exists. No action needed.')
                return
            
            # Create UserAccount table SQL
            self.stdout.write('Generating SQL to create UserAccount table...')
            # Include CREATE TABLE statements here
            sql = self.generate_create_tables_sql()
            
            # Write SQL to a file
            with open('migration_fix.sql', 'w') as f:
                f.write(sql)
            
            self.stdout.write(
                'SQL has been written to migration_fix.sql. ' +
                'To fix the issue in production, execute this SQL in your database.'
            )
        except Exception as e:
            self.stdout.write(f'Error: {str(e)}')
    
    def check_table_exists(self, table_name):
        """Check if the specified table exists in the database."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_name = %s
                """, [table_name])
                return cursor.fetchone()[0] > 0
        except Exception as e:
            self.stdout.write(f'Error checking table: {str(e)}')
            return False

    def generate_create_tables_sql(self):
        """Generate SQL statements to create necessary tables."""
        return """
-- Create the UserAccount table
CREATE TABLE "session_tracker_useraccount" (
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

-- Create the site table
CREATE TABLE "session_tracker_site" (
    "id" uuid NOT NULL PRIMARY KEY,
    "name" varchar(255) NOT NULL,
    "domain" varchar(255) NULL,
    "key" varchar(64) NULL UNIQUE,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "user_id" uuid NOT NULL REFERENCES "session_tracker_useraccount" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Create the UserProfile table
CREATE TABLE "session_tracker_userprofile" (
    "id" uuid NOT NULL PRIMARY KEY,
    "timezone" varchar(50) NOT NULL,
    "user_id" uuid NOT NULL UNIQUE REFERENCES "session_tracker_useraccount" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Create the UserSession table
CREATE TABLE "session_tracker_usersession" (
    "id" uuid NOT NULL PRIMARY KEY,
    "session_id" varchar(255) NOT NULL UNIQUE,
    "user_id" varchar(255) NOT NULL,
    "events" jsonb NOT NULL,
    "live" boolean NOT NULL,
    "created_at" timestamp with time zone NOT NULL,
    "updated_at" timestamp with time zone NOT NULL,
    "site_id" uuid NOT NULL REFERENCES "session_tracker_site" ("id") DEFERRABLE INITIALLY DEFERRED,
    "current_ip_address" inet NULL
);

-- Create URLExclusionRule table
CREATE TABLE "session_tracker_urlexclusionrule" (
    "id" uuid NOT NULL PRIMARY KEY,
    "exclusion_type" varchar(20) NOT NULL,
    "domain" varchar(255) NULL,
    "url_pattern" varchar(255) NULL,
    "created_at" timestamp with time zone NOT NULL,
    "ip_address" inet NULL,
    "site_id" uuid NOT NULL REFERENCES "session_tracker_site" ("id") DEFERRABLE INITIALLY DEFERRED,
    "user_id" uuid NOT NULL REFERENCES "session_tracker_useraccount" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Create indexes for UserSession
CREATE INDEX "session_tra_session_ac2c0d_idx" ON "session_tracker_usersession" ("session_id");
CREATE INDEX "session_tra_user_id_3b0666_idx" ON "session_tracker_usersession" ("user_id");
CREATE INDEX "session_tra_created_e8db4f_idx" ON "session_tracker_usersession" ("created_at");

-- Create many-to-many tables for UserAccount
CREATE TABLE "session_tracker_useraccount_groups" (
    "id" bigserial NOT NULL PRIMARY KEY,
    "useraccount_id" uuid NOT NULL,
    "group_id" integer NOT NULL,
    UNIQUE ("useraccount_id", "group_id"),
    FOREIGN KEY ("useraccount_id") REFERENCES "session_tracker_useraccount" ("id") DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY ("group_id") REFERENCES "auth_group" ("id") DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE "session_tracker_useraccount_user_permissions" (
    "id" bigserial NOT NULL PRIMARY KEY,
    "useraccount_id" uuid NOT NULL,
    "permission_id" integer NOT NULL,
    UNIQUE ("useraccount_id", "permission_id"),
    FOREIGN KEY ("useraccount_id") REFERENCES "session_tracker_useraccount" ("id") DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY ("permission_id") REFERENCES "auth_permission" ("id") DEFERRABLE INITIALLY DEFERRED
);

-- Finally mark the migration as applied
INSERT INTO django_migrations (app, name, applied) 
VALUES 
    ('session_tracker', '0001_initial', NOW()),
    ('session_tracker', '0002_alter_usersession_site', NOW()),
    ('session_tracker', '0003_alter_site_domain', NOW()),
    ('session_tracker', '0004_alter_usersession_events', NOW()),
    ('session_tracker', '0005_alter_usersession_events', NOW()),
    ('session_tracker', '0006_urlexclusionrule_ip_address_and_more', NOW()),
    ('session_tracker', '0007_usersession_current_ip_address', NOW());
""" 