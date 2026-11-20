from django.contrib import admin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import (
    Collaboration,
    EmailVerification,
    Invitation,
    Project,
    ProjectRole,
    Skill,
    User,
    UserSkill,
)


class AdminUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = (
            "email",
            "full_name",
            "user_type",
            "academic_program",
            "gender",
            "admission_year",
            "npm",
        )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("user_type") == User.UserType.STUDENT:
            if not cleaned_data.get("admission_year"):
                self.add_error("admission_year", "Angkatan wajib diisi untuk mahasiswa.")
            if not cleaned_data.get("npm"):
                self.add_error("npm", "NPM wajib diisi untuk mahasiswa.")
        else:
            cleaned_data["admission_year"] = None
            cleaned_data["npm"] = None
        return cleaned_data


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = AdminUserCreationForm
    ordering = ("email",)
    list_display = (
        "email",
        "full_name",
        "user_type",
        "npm",
        "availability",
        "is_campus_verified",
        "is_active",
    )
    list_filter = ("user_type", "availability", "is_campus_verified", "is_demo")
    search_fields = ("email", "full_name", "npm", "academic_program")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Profil",
            {
                "fields": (
                    "full_name",
                    "user_type",
                    "academic_program",
                    "gender",
                    "admission_year",
                    "npm",
                    "github_url",
                    "availability",
                )
            },
        ),
        ("Verifikasi", {"fields": ("is_campus_verified", "verified_at")}),
        (
            "Hak akses",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "is_demo",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Tanggal", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "user_type",
                    "academic_program",
                    "gender",
                    "admission_year",
                    "npm",
                    "password1",
                    "password2",
                ),
            },
        ),
    )
    readonly_fields = ("verified_at", "last_login", "date_joined")
    filter_horizontal = ("groups", "user_permissions")
    username_field = "email"


admin.site.register(EmailVerification)
admin.site.register(Skill)
admin.site.register(UserSkill)
admin.site.register(Project)
admin.site.register(ProjectRole)
admin.site.register(Invitation)
admin.site.register(Collaboration)
