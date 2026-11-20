import re

from django import forms
from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from .models import Skill, User


class RegistrationForm(forms.Form):
    full_name = forms.CharField(max_length=150)
    user_type = forms.ChoiceField(
        choices=User.UserType.choices, required=False, initial=User.UserType.STUDENT
    )
    academic_program = forms.CharField(max_length=120, required=False)
    gender = forms.ChoiceField(choices=User.Gender.choices)
    admission_year = forms.IntegerField(min_value=1900, max_value=9999, required=False)
    npm = forms.CharField(max_length=15, min_length=8, required=False)
    email = forms.EmailField(max_length=254)
    password = forms.CharField(
        min_length=8, max_length=128, strip=False, widget=forms.PasswordInput
    )

    def clean_full_name(self):
        value = self.cleaned_data["full_name"].strip()
        if not value:
            raise ValidationError("Nama lengkap wajib diisi.")
        return value

    def clean_npm(self):
        value = self.cleaned_data["npm"].strip()
        if not value:
            return ""
        if not re.fullmatch(r"[0-9]{8,15}", value):
            raise ValidationError("NPM harus terdiri dari 8-15 digit.")
        if User.objects.filter(npm=value).exists():
            raise ValidationError("NPM sudah terdaftar.")
        return value

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Email sudah terdaftar.")
        domain = getattr(settings, "CAMPUS_EMAIL_DOMAIN", "")
        if domain and email.rsplit("@", 1)[-1] != domain.lower().lstrip("@"):
            raise ValidationError("Gunakan email kampus yang terdaftar.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get("user_type") or User.UserType.STUDENT
        cleaned_data["user_type"] = user_type
        if user_type == User.UserType.STUDENT:
            if not cleaned_data.get("admission_year"):
                self.add_error("admission_year", "Angkatan wajib diisi untuk mahasiswa.")
            if not cleaned_data.get("npm"):
                self.add_error("npm", "NPM wajib diisi untuk mahasiswa.")
        else:
            cleaned_data["admission_year"] = None
            cleaned_data["npm"] = None

        if cleaned_data.get("password"):
            candidate = User(
                email=cleaned_data.get("email", ""),
                full_name=cleaned_data.get("full_name", ""),
                npm=cleaned_data.get("npm", ""),
            )
            validate_password(cleaned_data["password"], user=candidate)
        return cleaned_data

    def create_user(self):
        return User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            full_name=self.cleaned_data["full_name"],
            gender=self.cleaned_data["gender"],
            admission_year=self.cleaned_data["admission_year"],
            npm=self.cleaned_data["npm"],
            user_type=self.cleaned_data["user_type"],
            academic_program=self.cleaned_data["academic_program"].strip(),
        )


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "full_name",
            "gender",
            "admission_year",
            "academic_program",
            "github_url",
            "availability",
        ]

    def clean_full_name(self):
        value = self.cleaned_data["full_name"].strip()
        if not value:
            raise ValidationError("Nama lengkap wajib diisi.")
        return value


class SkillNameForm(forms.Form):
    name = forms.CharField(max_length=80)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        slug = slugify(name.casefold())
        if not name or not slug or not re.fullmatch(r"[\w+#.\- ]{1,80}", name, re.UNICODE):
            raise ValidationError("Nama skill tidak valid.")
        self.cleaned_data["slug"] = slug[:100]
        return name

    def get_or_create_skill(self):
        skill, _ = Skill.objects.get_or_create(
            slug=self.cleaned_data["slug"],
            defaults={"name": self.cleaned_data["name"]},
        )
        return skill
