# Deployment Fix for Migration Issues

## Overview

This document explains how to fix the migration issues encountered in the production environment, where the error `psycopg2.errors.UndefinedTable: relation "session_tracker_useraccount" does not exist` is occurring.

## Solution

We've created two special migrations that will automatically fix the database schema without any manual intervention:

1. `0008_fix_missing_tables.py` - Creates any missing tables that should have been created by earlier migrations
2. `0009_fix_migration_records.py` - Ensures all migration records are properly recorded in the django_migrations table

## Deployment Steps

1. **Deploy the updated code** to Railway.com with these new migrations included

2. **The migration will run automatically** when Railway's deployment process executes the standard migrate command

3. **No manual SQL execution is required** - everything is handled in the migration files

## Verification

After deployment, you should be able to verify that:

1. All tables now exist in the database
2. The application starts successfully without migration errors
3. The admin interface works as expected

## Technical Details

The migration fix works by:

1. Checking if the `session_tracker_useraccount` table exists in the database
2. If not, it creates all required tables with the correct structure
3. It adds foreign key constraints for relationships between tables
4. It ensures all migration records are properly recorded in the django_migrations table

This approach is safe to run multiple times, as it only creates tables and records if they don't already exist.

## Troubleshooting

If you continue to experience issues after deploying this fix:

1. Check the deployment logs to see if the migrations are being applied
2. If needed, you can manually trigger the migration process in Railway by running a custom command
3. Contact the development team for further assistance

## Prevention

To prevent similar issues in the future:

1. Always ensure database migrations are part of the CI/CD pipeline testing
2. Create database schema verification tests
3. Consider using Django's test suite to verify migrations before deployment 