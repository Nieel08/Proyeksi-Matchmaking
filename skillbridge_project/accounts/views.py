import json
import logging
import secrets
import smtplib
from datetime import timedelta
from json import JSONDecodeError

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .forms import ProfileForm, RegistrationForm, SkillNameForm
from .models import EmailVerification, User, UserSkill


logger = logging.getLogger(__name__)
OTP_EXPIRY_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _json_body(request):
    if request.content_type != "application/json":
        return request.POST.dict(), None
    try:
        body = json.loads(request.body)
    except (JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({"error": "JSON tidak valid."}, status=400)
    if not isinstance(body, dict):
        return None, JsonResponse({"error": "Body harus berupa objek JSON."}, status=400)
    return body, None


def _form_errors(form):
    return {
        field: [error["message"] for error in errors]
        for field, errors in form.errors.get_json_data().items()
    }


def _user_payload(user):
    return {
        "id": user.pk,
        "full_name": user.full_name,
        "gender": user.gender,
        "admission_year": user.admission_year,
        "npm": user.npm,
        "email": user.email,
        "is_campus_verified": user.is_campus_verified,
        "verified_at": user.verified_at.isoformat() if user.verified_at else None,
        "github_url": user.github_url,
        "availability": user.availability,
        "skills": [
            {"id": item.skill_id, "name": item.skill.name}
            for item in user.user_skills.select_related("skill").order_by("skill__name")
        ],
    }


def _api_user(request):
    if not request.user.is_authenticated:
        return None, JsonResponse({"error": "Autentikasi diperlukan."}, status=401)
    if not request.user.is_campus_verified:
        return None, JsonResponse({"error": "Akun belum terverifikasi."}, status=403)
    return request.user, None


@require_GET
@never_cache
def csrf_token(request):
    return JsonResponse({"csrfToken": get_token(request)})


@require_POST
@never_cache
def register(request):
    data, error = _json_body(request)
    if error:
        return error

    form = RegistrationForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": _form_errors(form)}, status=400)

    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        with transaction.atomic():
            user = form.create_user()
            EmailVerification.objects.create(
                user=user,
                token_hash=make_password(code),
                expires_at=timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES),
            )
            send_mail(
                subject="Kode verifikasi akun",
                message=(
                    f"Kode verifikasi akun SkillBridge Anda: {code}\n"
                    f"Kode berlaku selama {OTP_EXPIRY_MINUTES} menit."
                ),
                from_email=None,
                recipient_list=[user.email],
                fail_silently=False,
            )
    except IntegrityError:
        return JsonResponse({"error": "Email atau NPM sudah terdaftar."}, status=400)
    except (OSError, smtplib.SMTPException):
        logger.exception("Pengiriman OTP gagal.")
        return JsonResponse(
            {"error": "Email verifikasi gagal dikirim. Coba lagi nanti."}, status=503
        )

    return JsonResponse(
        {"message": "Pendaftaran berhasil. Masukkan kode yang dikirim ke email kampus."},
        status=201,
    )


@require_POST
@never_cache
def verify_email(request):
    data, error = _json_body(request)
    if error:
        return error
    email = data.get("email", "")
    code = data.get("code", "")
    if not isinstance(email, str) or not isinstance(code, str):
        return JsonResponse({"error": "Email dan kode verifikasi wajib berupa teks."}, status=400)
    email = email.strip().lower()
    if not code.isdigit() or len(code) != 6:
        return JsonResponse({"error": "Kode verifikasi tidak valid atau kedaluwarsa."}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.get(email__iexact=email)
            verification = (
                EmailVerification.objects.select_for_update()
                .filter(user=user, consumed_at__isnull=True)
                .order_by("-created_at")
                .first()
            )
            now = timezone.now()
            if not verification:
                return JsonResponse(
                    {"error": "Kode verifikasi tidak valid atau kedaluwarsa."}, status=400
                )
            if (
                verification.expires_at <= now
                or verification.attempts >= OTP_MAX_ATTEMPTS
                or not check_password(code, verification.token_hash)
            ):
                if verification.attempts < OTP_MAX_ATTEMPTS and verification.expires_at > now:
                    verification.attempts += 1
                    if verification.attempts >= OTP_MAX_ATTEMPTS:
                        verification.consumed_at = now
                    verification.save(update_fields=["attempts", "consumed_at"])
                elif verification.expires_at <= now:
                    verification.consumed_at = now
                    verification.save(update_fields=["consumed_at"])
                return JsonResponse(
                    {"error": "Kode verifikasi tidak valid atau kedaluwarsa."}, status=400
                )

            user.is_campus_verified = True
            user.verified_at = now
            user.save(update_fields=["is_campus_verified", "verified_at"])
            verification.consumed_at = now
            verification.save(update_fields=["consumed_at"])
    except User.DoesNotExist:
        return JsonResponse({"error": "Kode verifikasi tidak valid atau kedaluwarsa."}, status=400)

    return JsonResponse({"message": "Email kampus berhasil diverifikasi."})


@require_POST
@never_cache
def login_view(request):
    data, error = _json_body(request)
    if error:
        return error
    email = data.get("email", "")
    password = data.get("password", "")
    if not isinstance(email, str) or not isinstance(password, str):
        return JsonResponse({"error": "Email dan sandi wajib diisi."}, status=400)
    user = authenticate(request, username=email.strip().lower(), password=password)
    if user is None:
        return JsonResponse({"error": "Email atau sandi salah."}, status=400)
    if not user.is_campus_verified:
        return JsonResponse({"error": "Akun belum terverifikasi."}, status=403)
    login(request, user)
    return JsonResponse({"message": "Login berhasil.", "user": _user_payload(user)})


@require_POST
@never_cache
def logout_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Autentikasi diperlukan."}, status=401)
    logout(request)
    return JsonResponse({"message": "Logout berhasil."})


@require_GET
def profile(request):
    user, error = _api_user(request)
    if error:
        return error
    return JsonResponse({"user": _user_payload(user)})


@require_http_methods(["PUT", "PATCH"])
def update_profile(request):
    user, error = _api_user(request)
    if error:
        return error
    data, error = _json_body(request)
    if error:
        return error
    allowed_fields = {"full_name", "gender", "admission_year", "github_url", "availability"}
    if set(data) - allowed_fields:
        return JsonResponse({"error": "Ada field profil yang tidak diizinkan."}, status=400)
    current = {field: getattr(user, field) for field in allowed_fields}
    form = ProfileForm({**current, **data}, instance=user)
    if not form.is_valid():
        return JsonResponse({"errors": _form_errors(form)}, status=400)
    form.save()
    return JsonResponse({"user": _user_payload(user)})


@require_POST
def skill_collection(request):
    user, error = _api_user(request)
    if error:
        return error
    data, error = _json_body(request)
    if error:
        return error
    form = SkillNameForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": _form_errors(form)}, status=400)
    try:
        with transaction.atomic():
            skill = form.get_or_create_skill()
            assignment, created = UserSkill.objects.get_or_create(user=user, skill=skill)
    except IntegrityError:
        assignment = UserSkill.objects.get(user=user, skill__slug=form.cleaned_data["slug"])
        created = False
    return JsonResponse(
        {"skill": {"id": assignment.pk, "name": assignment.skill.name}},
        status=201 if created else 200,
    )


@require_http_methods(["PUT", "PATCH"])
def update_skill(request, assignment_id):
    user, error = _api_user(request)
    if error:
        return error
    data, error = _json_body(request)
    if error:
        return error
    assignment = (
        UserSkill.objects.filter(user=user, pk=assignment_id).select_related("skill").first()
    )
    if assignment is None:
        return JsonResponse({"error": "Skill tidak ditemukan."}, status=404)
    form = SkillNameForm(data)
    if not form.is_valid():
        return JsonResponse({"errors": _form_errors(form)}, status=400)
    try:
        with transaction.atomic():
            if (
                assignment.skill.slug != form.cleaned_data["slug"]
                and UserSkill.objects.filter(
                    user=user, skill__slug=form.cleaned_data["slug"]
                ).exists()
            ):
                return JsonResponse(
                    {"error": "Skill tersebut sudah ada di profil."}, status=400
                )
            new_skill = form.get_or_create_skill()
            assignment.skill = new_skill
            assignment.save(update_fields=["skill"])
    except IntegrityError:
        return JsonResponse({"error": "Skill tersebut sudah ada di profil."}, status=400)
    return JsonResponse({"skill": {"id": assignment.pk, "name": assignment.skill.name}})


@require_http_methods(["DELETE"])
def delete_skill(request, assignment_id):
    user, error = _api_user(request)
    if error:
        return error
    deleted, _ = UserSkill.objects.filter(user=user, pk=assignment_id).delete()
    if not deleted:
        return JsonResponse({"error": "Skill tidak ditemukan."}, status=404)
    return JsonResponse({"message": "Skill dihapus dari profil."})
