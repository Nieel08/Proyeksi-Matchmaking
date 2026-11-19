from django.urls import path

from . import views


app_name = "accounts"

urlpatterns = [
    path("csrf/", views.csrf_token, name="csrf"),
    path("auth/register/", views.register, name="register"),
    path("auth/verify-email/", views.verify_email, name="verify-email"),
    path("auth/login/", views.login_view, name="login"),
    path("auth/logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("profile/update/", views.update_profile, name="profile-update"),
    path("profile/skills/", views.skill_collection, name="skill-collection"),
    path("profile/skills/<int:assignment_id>/", views.update_skill, name="skill-update"),
    path("profile/skills/<int:assignment_id>/delete/", views.delete_skill, name="skill-delete"),
]
