from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone

from .validators import validate_github_profile_url


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email wajib diisi.")
        user = self.model(email=self.normalize_email(email).strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser harus memiliki is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser harus memiliki is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    class Gender(models.TextChoices):
        MALE = "male", "Laki-laki"
        FEMALE = "female", "Perempuan"
        OTHER = "other", "Lainnya"

    class Availability(models.TextChoices):
        READY = "ready", "Ready"
        BUSY = "busy", "Busy"

    full_name = models.CharField(max_length=150)
    gender = models.CharField(max_length=10, choices=Gender.choices)
    admission_year = models.PositiveSmallIntegerField(
        validators=[RegexValidator(r"^[0-9]{4}$", "Angkatan harus terdiri dari 4 digit.")]
    )
    npm = models.CharField(
        max_length=15,
        unique=True,
        validators=[RegexValidator(r"^[0-9]{8,15}$", "NPM harus terdiri dari 8-15 digit.")],
    )
    email = models.EmailField(max_length=254, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_campus_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    github_url = models.URLField(
        max_length=200, blank=True, validators=[validate_github_profile_url]
    )
    availability = models.CharField(
        max_length=10, choices=Availability.choices, default=Availability.READY
    )
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name", "gender", "admission_year", "npm"]

    class Meta:
        db_table = "users"
        constraints = [
            models.UniqueConstraint(Lower("email"), name="users_email_ci_unique"),
        ]

    def __str__(self):
        return self.email


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verifications")
    token_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    consumed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "email_verifications"
        indexes = [models.Index(fields=["user", "expires_at"])]


class Skill(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        db_table = "skills"
        ordering = ["name"]

    def __str__(self):
        return self.name


class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="user_skills")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "user_skills"
        constraints = [
            models.UniqueConstraint(fields=["user", "skill"], name="user_skill_unique"),
        ]


class Project(models.Model):
    # --- DITAMBAHKAN OLEH NATALIE (modul Posting Proyek) ---
    class ProjectType(models.TextChoices):
        LOMBA = "lomba", "Lomba"
        KULIAH = "kuliah", "Proyek Kuliah"
        PENELITIAN = "penelitian", "Penelitian"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Dipublikasikan"
        CLOSED = "closed", "Ditutup"
    # --------------------------------------------------------

    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="owned_projects")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    # --- DITAMBAHKAN OLEH NATALIE ---
    project_type = models.CharField(
        max_length=20, choices=ProjectType.choices, default=ProjectType.LOMBA
    )
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    updated_at = models.DateTimeField(auto_now=True)
    # --------------------------------

    class Meta:
        db_table = "projects"


class ProjectRole(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="roles")
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    # --- DITAMBAHKAN OLEH NATALIE ---
    slots_needed = models.PositiveIntegerField(default=1)
    slots_filled = models.PositiveIntegerField(default=0)
    required_skills = models.ManyToManyField(Skill, blank=True, related_name="project_roles")
    # --------------------------------

    class Meta:
        db_table = "project_roles"

    @property
    def slots_left(self):
        return max(self.slots_needed - self.slots_filled, 0)


class Invitation(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    project_role = models.ForeignKey(
        ProjectRole, on_delete=models.CASCADE, related_name="invitations"
    )
    sender = models.ForeignKey(User, on_delete=models.PROTECT, related_name="sent_invitations")
    recipient = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="received_invitations"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "invitations"


class Collaboration(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ENDED = "ended", "Ended"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="collaborations")
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="collaborations")
    project_role = models.ForeignKey(
        ProjectRole, on_delete=models.PROTECT, related_name="collaborations"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "collaborations"
