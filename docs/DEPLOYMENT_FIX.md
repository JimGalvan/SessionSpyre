# Deployment Fix for Migration Issues

## Overview

This document explains how to fix the migration issues encountered in the production environment, where the error `psycopg2.errors.UndefinedTable: relation "session_tracker_useraccount" does not exist` is occurring.

## Solution

We've created a Django management command that will set up the necessary tables before running migrations:

1. `setup_initial_tables` - Creates the essential tables before any migrations run
2. Regular migrations will then run normally after tables are created

## Deployment Steps

1. **SSH into your Railway.com environment** or use the Railway CLI

2. **Run the setup command first**:
   ```bash
   python manage.py setup_initial_tables
   ```

3. **Then run migrations**:
   ```bash
   python manage.py migrate
   ```

## Verification

After deployment, you should be able to verify that:

1. The `session_tracker_useraccount` table exists in the database
2. All migrations run successfully
3. The admin interface works as expected

## Technical Details

The fix works by:

1. Using a custom management command to create the essential `session_tracker_useraccount` table
2. Creating the table with the exact schema needed by Django
3. Using `IF NOT EXISTS` to ensure the command is safe to run multiple times
4. Running this setup before any migrations attempt to use the table

This approach is safe and idempotent - it can be run multiple times without causing issues.

## Troubleshooting

If you experience issues:

1. Check that you can connect to the database
2. Verify the setup command runs without errors
3. Look for any error messages in the migration output
4. Contact the development team if issues persist

## Prevention

To prevent similar issues in the future:

1. Always ensure database migrations are part of the CI/CD pipeline testing
2. Create database schema verification tests
3. Consider using Django's test suite to verify migrations before deployment
4. Add pre-deployment checks for required database structures 