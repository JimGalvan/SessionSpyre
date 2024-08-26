from django.conf import settings
from django.contrib import admin
from django.contrib.auth.views import logout_then_login
from django.urls import path

from session_tracker.api import api
from session_tracker.views import session_views as sessions_views
from session_tracker.views import sessions_views_test as sessions_views_test
from session_tracker.views import user_views as user_views

urlpatterns = [
    path('', user_views.index, name='index'),
    path("api/", api.urls),
    path('login/', user_views.Login.as_view(), name='login'),
    path('logout/', logout_then_login, {'login_url': '/'}, name='logout'),
    path("register/", user_views.RegisterView.as_view(), name="register"),
    path('accounts/profile/', user_views.profile_view, name='profile'),
    path('update-timezone/', user_views.update_timezone, name='update_timezone'),
    path('set-timezone/', user_views.set_timezone, name='set_timezone'),
    path('check-timezone/', user_views.check_timezone, name='check_timezone'),
    # path('sessions_view/', sessions_views.sessions_view, name='sessions_view'),
    # path('sessions_list/', sessions_views.sessions_list, name='sessions_list'),
    path('replay_session/<str:session_id>/', sessions_views.replay_session, name='replay_session'),
    path('delete_session/<str:session_id>/', sessions_views.delete_session, name='delete_session'),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    test_urlpatterns = [
        path('sessions_view/', sessions_views_test.sessions_view, name='sessions_view'),
        path('sessions_list/', sessions_views_test.sessions_list, name='sessions_list'),
    ]
    urlpatterns += test_urlpatterns
