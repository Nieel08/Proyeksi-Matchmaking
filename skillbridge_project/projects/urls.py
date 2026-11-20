from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("saya/", views.my_projects, name="mine"),
    path("baru/", views.project_form, name="create"),
    path("<int:pk>/", views.project_detail, name="detail"),
    path("<int:pk>/edit/", views.project_form, name="edit"),
    path("<int:pk>/hapus/", views.project_delete, name="delete"),
    path("<int:pk>/publikasi/", views.project_publish, name="publish"),
    path("<int:pk>/tutup/", views.project_close, name="close"),
]
