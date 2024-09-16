from .base import *
import os
import dj_database_url

DEBUG = True

# Reading .os.getenv file
# environ.Env.read_env(os.path.join(BASE_DIR, '.os.getenv'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = str(os.getenv('SECRET_KEY'))

ALLOWED_HOSTS = ['*']

print("DATABASE_URL: ", os.getenv('DATABASE_URL'))
print("ENGINE: ", os.getenv('DB_ENGINE', default='django.db.backends.postgresql'))
print("NAME: ", os.getenv('DB_NAME'))
print("USER: ", os.getenv('DB_USER'))
print("PASSWORD: ", os.getenv('DB_PASSWORD'))
print("HOST: ", os.getenv('DB_HOST', default='localhost'))
print("PORT: ", os.getenv('DB_PORT', default='5432'))

# DATABASES = {
#     'default': {
#         'ENGINE': os.getenv('DB_ENGINE', default='django.db.backends.postgresql'),
#         'NAME': os.getenv('DB_NAME'),
#         'USER': os.getenv('DB_USER'),
#         'PASSWORD': os.getenv('DB_PASSWORD'),
#         'HOST': os.getenv('DB_HOST', default='localhost'),
#         'PORT': os.getenv('DB_PORT', default='5432'),
#     }
# }

DATABASES = {
    'default': dj_database_url.config(default=os.getenv('DATABASE_URL'))
}

CSRF_TRUSTED_ORIGINS = [
    'https://sessionspyre-production.up.railway.app'
]

SCRIPT_URL = 'https://a3d3b857.sessionspyre-clientjs.pages.dev/record.js'
