from django.contrib import admin
from django.contrib.auth.views import logout_then_login
from django.urls import path, include

from session_tracker.api import api
from session_tracker.views import session_views as sessions_views
from session_tracker.views import url_exclusion_rule_views as url_exclusion_rule_views
from session_tracker.views import user_views as user_views
from session_tracker.views.site_views import create_site, delete_site, update_site, sites_view, \
    get_snippet_data

urlpatterns = [
    path('', user_views.index, name='index'),
    path("api/", api.urls),
    path('login', user_views.Login.as_view(), name='login'),
    path('logout', logout_then_login, {'login_url': '/'}, name='logout'),
    path("register", user_views.RegisterView.as_view(), name="register"),
    path('admin', admin.site.urls),
    path('accounts/profile/', user_views.profile_view, name='profile'),
    path('update-timezon', user_views.update_timezone, name='update_timezone'),
    path('set-timezone', user_views.set_timezone, name='set_timezone'),
    path('check-timezone', user_views.check_timezone, name='check_timezone'),
    path('sessions_view/<str:site_id>', sessions_views.sessions_view, name='sessions_view'),
    path('sessions_list/<str:site_id>', sessions_views.sessions_list, name='sessions_list'),
    path('replay_session/<str:session_id>', sessions_views.replay_session, name='replay_session'),
    path('delete_session/<str:session_id>', sessions_views.delete_session, name='delete_session'),
    path('sites', sites_view, name='sites_view'),
    path('sites/create', create_site, name='create_site'),
    path('sites/update/<str:site_id>', update_site, name='update_site'),
    path('sites/delete/<str:site_id>', delete_site, name='delete_site'),
    path('sites/get-snippet-data/user/<str:user_id>/site/<str:site_id>', get_snippet_data, name='get_snippet_data'),
    path('sites/<str:site_id>/url_exclusions', url_exclusion_rule_views.get_url_exclusions, name='get_url_exclusions'),
    path('sites/<str:site_id>/add-url-exclusion', url_exclusion_rule_views.add_url_exclusion, name='add_url_exclusion'),
    path('url-exclusion/delete/<str:rule_id>', url_exclusion_rule_views.delete_url_exclusion,
         name='delete_url_exclusion'),
    path("__reload__/", include("django_browser_reload.urls")),
]
