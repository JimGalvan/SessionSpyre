# Fixing Migration Issues in Production

This document provides instructions on how to fix the migrations issue in the production environment where Django is encountering: `psycopg2.errors.UndefinedTable: relation "session_tracker_useraccount" does not exist`.

## Option 1: Using the Management Command

We've created a custom Django management command to generate the necessary SQL to fix the database schema:

1. Deploy the latest code to production which includes the management command
2. Run the command in your production environment:

```bash
python manage.py reset_migrations
```

3. This will generate a file named `migration_fix.sql` with all the SQL statements needed to create the missing tables
4. Execute this SQL against your production database:

```bash
# If using PostgreSQL
psql -U your_db_user -d your_db_name -f migration_fix.sql
```

## Option 2: Manual Database Reset (If Option 1 Doesn't Work)

If the management command doesn't solve the issue, you can try a more thorough approach:

1. Back up your production database (VERY IMPORTANT)

2. Connect to your database and delete all Django migrations records for the session_tracker app:

```sql
DELETE FROM django_migrations WHERE app = 'session_tracker';
```

3. Drop all tables related to the session_tracker app (make sure you have a backup first!):

```sql
DROP TABLE IF EXISTS session_tracker_useraccount_groups;
DROP TABLE IF EXISTS session_tracker_useraccount_user_permissions;
DROP TABLE IF EXISTS session_tracker_urlexclusionrule;
DROP TABLE IF EXISTS session_tracker_usersession;
DROP TABLE IF EXISTS session_tracker_userprofile;
DROP TABLE IF EXISTS session_tracker_site;
DROP TABLE IF EXISTS session_tracker_useraccount;
```

4. Run Django migrations to recreate the schema:

```bash
python manage.py migrate
```

## Option 3: Direct SQL Execution

If you cannot deploy the management command to production, here is the SQL you need to execute:

```sql
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
```

## Preventative Measures

To avoid this issue in the future:

1. Always run `python manage.py migrate` when setting up a new instance
2. Make sure all models are properly defined before generating migrations
3. Consider using a migration testing tool/workflow to detect issues early 