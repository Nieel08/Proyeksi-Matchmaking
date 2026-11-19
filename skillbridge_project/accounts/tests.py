import json
import re

from django.contrib.auth.hashers import check_password
from django.core import mail
from django.test import Client, TestCase, override_settings

from .models import EmailVerification, User, UserSkill


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AccountsApiTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        response = self.client.get("/api/csrf/")
        self.csrf_token = response.json()["csrfToken"]
        self.headers = {"HTTP_X_CSRFTOKEN": self.csrf_token}
        self.registration_data = {
            "full_name": "Mahasiswa Contoh",
            "gender": "other",
            "admission_year": 2024,
            "npm": "02630240022",
            "email": " Student@kampus.ac.id ",
            "password": "J4m!n-Strong-Password",
        }

    def post_json(self, url, data):
        return self.client.post(
            url,
            data=json.dumps(data),
            content_type="application/json",
            **self.headers,
        )

    def register_and_verify(self):
        response = self.post_json("/api/auth/register/", self.registration_data)
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="student@kampus.ac.id")
        verification = EmailVerification.objects.get(user=user)
        code = re.search(r"\b\d{6}\b", mail.outbox[0].body).group()
        self.assertNotEqual(verification.token_hash, code)
        self.assertTrue(check_password(code, verification.token_hash))
        return user, code

    def test_registration_hashes_password_and_verification_is_one_time(self):
        user, code = self.register_and_verify()
        self.assertNotEqual(user.password, self.registration_data["password"])
        self.assertTrue(check_password(self.registration_data["password"], user.password))
        self.assertFalse(user.is_campus_verified)

        response = self.post_json(
            "/api/auth/verify-email/", {"email": user.email.upper(), "code": code}
        )
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_campus_verified)
        verification = EmailVerification.objects.get(user=user)
        self.assertIsNotNone(verification.consumed_at)

        second_use = self.post_json(
            "/api/auth/verify-email/", {"email": user.email, "code": code}
        )
        self.assertEqual(second_use.status_code, 400)

    def test_verification_code_is_locked_after_five_wrong_attempts(self):
        user, code = self.register_and_verify()
        wrong_code = "000000" if code != "000000" else "000001"
        for _ in range(5):
            response = self.post_json(
                "/api/auth/verify-email/", {"email": user.email, "code": wrong_code}
            )
            self.assertEqual(response.status_code, 400)

        locked_out = self.post_json(
            "/api/auth/verify-email/", {"email": user.email, "code": code}
        )
        self.assertEqual(locked_out.status_code, 400)
        user.refresh_from_db()
        self.assertFalse(user.is_campus_verified)

    def test_superuser_manager_sets_required_access_flags(self):
        admin_user = User.objects.create_superuser(
            email="admin@kampus.ac.id",
            password="Secure-Admin-Password-2026!",
            full_name="Admin Kampus",
            gender="other",
            admission_year=2020,
            npm="12345678",
        )
        self.assertTrue(admin_user.is_staff)
        self.assertTrue(admin_user.is_superuser)

    def test_csrf_required_and_profile_requires_verified_login(self):
        rejected = self.client.post(
            "/api/auth/register/",
            data=json.dumps(self.registration_data),
            content_type="application/json",
        )
        self.assertEqual(rejected.status_code, 403)

        user, _ = self.register_and_verify()
        response = self.post_json(
            "/api/auth/login/",
            {"email": user.email, "password": self.registration_data["password"]},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.get("/api/profile/").status_code, 401)

    def test_login_skills_and_github_validation(self):
        user, code = self.register_and_verify()
        self.post_json("/api/auth/verify-email/", {"email": user.email, "code": code})
        login_response = self.post_json(
            "/api/auth/login/",
            {"email": " STUDENT@KAMPUS.AC.ID ", "password": self.registration_data["password"]},
        )
        self.assertEqual(login_response.status_code, 200)
        self.csrf_token = self.client.get("/api/csrf/").json()["csrfToken"]
        self.headers = {"HTTP_X_CSRFTOKEN": self.csrf_token}

        valid_url = self.client.patch(
            "/api/profile/update/",
            data=json.dumps({"github_url": "https://github.com/student-123"}),
            content_type="application/json",
            **self.headers,
        )
        self.assertEqual(valid_url.status_code, 200)
        for url in (
            "javascript:alert(1)",
            "data:text/html,test",
            "http://github.com/student",
            "https://github.com.evil.example/student",
            "https://github.com/student/repository",
        ):
            with self.subTest(url=url):
                invalid_url = self.client.patch(
                    "/api/profile/update/",
                    data=json.dumps({"github_url": url}),
                    content_type="application/json",
                    **self.headers,
                )
                self.assertEqual(invalid_url.status_code, 400)

        first = self.post_json("/api/profile/skills/", {"name": "Python"})
        duplicate = self.post_json("/api/profile/skills/", {"name": " python "})
        self.assertEqual(first.status_code, 201)
        self.assertEqual(duplicate.status_code, 200)
        self.assertEqual(UserSkill.objects.filter(user=user).count(), 1)
