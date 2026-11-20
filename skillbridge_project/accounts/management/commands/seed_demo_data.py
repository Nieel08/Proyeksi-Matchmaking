from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import (
    Project,
    ProjectRole,
    Skill,
    User,
    UserSkill,
)


DEMO_MEMBERS = [
    ("Rizky Pratama", "student", "Teknik Informatika", 2023, "ready", "male", ["Python", "Django", "PostgreSQL"]),
    ("Nabila Putri", "student", "Desain Komunikasi Visual", 2022, "ready", "female", ["UI/UX", "Figma", "Riset Pengguna"]),
    ("Farhan Akbar", "student", "Sistem Informasi", 2021, "busy", "male", ["React", "TypeScript", "UI/UX"]),
    ("Salsabila Rahman", "student", "Statistika", 2023, "ready", "female", ["Python", "Data Science", "Machine Learning"]),
    ("Kevin Wijaya", "student", "Teknik Informatika", 2022, "ready", "male", ["Flutter", "Firebase", "UI/UX"]),
    ("Intan Permata", "student", "Manajemen", 2024, "busy", "female", ["Riset Pengguna", "Product Management", "Presentasi"]),
    ("Bagas Ramadhan", "student", "Teknik Elektro", 2021, "ready", "male", ["Internet of Things", "Python", "Elektronika"]),
    ("Maya Safitri", "student", "Ilmu Komunikasi", 2023, "busy", "female", ["Penulisan", "Media Sosial", "Presentasi"]),
    ("Dimas Arya", "student", "Teknik Informatika", 2022, "ready", "male", ["Java", "Spring Boot", "PostgreSQL"]),
    ("Citra Maharani", "student", "Desain Komunikasi Visual", 2024, "ready", "female", ["Figma", "Branding", "Ilustrasi"]),
    ("Aditya Nugraha", "student", "Matematika", 2020, "busy", "male", ["Statistika", "Python", "Data Science"]),
    ("Lestari Wulandari", "student", "Bisnis Digital", 2022, "ready", "female", ["Pemasaran", "Penulisan", "Riset Pengguna"]),
    ("Bintang Mahesa", "student", "Teknik Informatika", 2023, "ready", "male", ["Docker", "Django", "Cloud"]),
    ("Putri Amalia", "student", "Akuntansi", 2021, "busy", "female", ["Analisis Data", "Excel", "Presentasi"]),
    ("Arga Saputra", "student", "Sistem Informasi", 2024, "ready", "male", ["React", "Figma", "JavaScript"]),
    ("Dr. Andini Prameswari", "lecturer", "Dosen Informatika · Riset AI", None, "ready", "female", ["Machine Learning", "Python", "Riset"]),
    ("Dr. Budi Santoso", "lecturer", "Dosen Statistika · Analitik Data", None, "busy", "male", ["Statistika", "Data Science", "Riset"]),
    ("Dr. Rina Kusuma", "lecturer", "Dosen Desain · Inovasi Digital", None, "ready", "female", ["UI/UX", "Riset Pengguna", "Product Management"]),
    ("Dr. Adi Pranata", "lecturer", "Dosen Teknik Elektro · IoT", None, "busy", "male", ["Internet of Things", "Elektronika", "Cloud"]),
]

DEMO_PROJECTS = [
    {
        "owner_email": "demo.member16@skillbridge.example",
        "title": "[Demo] Peta Kualitas Udara Kampus",
        "description": "Membangun dashboard data sensor untuk membantu komunitas kampus memahami kualitas udara.",
        "project_type": Project.ProjectType.PENELITIAN,
        "role_name": "Data & Backend",
        "skills": ["Python", "Data Science", "Django"],
    },
    {
        "owner_email": "demo.member02@skillbridge.example",
        "title": "[Demo] Aplikasi Teman Belajar",
        "description": "Merancang ruang belajar kolaboratif yang mempertemukan mahasiswa lintas program studi.",
        "project_type": Project.ProjectType.KULIAH,
        "role_name": "Product Designer",
        "skills": ["UI/UX", "Figma", "Riset Pengguna"],
    },
    {
        "owner_email": "demo.member17@skillbridge.example",
        "title": "[Demo] Asisten Riset Terbuka",
        "description": "Proyek penelitian kolaboratif untuk mengelola dan menyajikan data secara mudah dipahami.",
        "project_type": Project.ProjectType.PENELITIAN,
        "role_name": "Asisten Analisis Data",
        "skills": ["Statistika", "Python", "Riset"],
    },
]


class Command(BaseCommand):
    help = "Tambahkan profil, skill, dan proyek contoh untuk demonstrasi lokal."

    def handle(self, *args, **options):
        skills = {}
        for member in DEMO_MEMBERS:
            for name in member[6]:
                skill, _ = Skill.objects.get_or_create(
                    slug=slugify(name),
                    defaults={"name": name},
                )
                skills[name] = skill

        demo_users = {}
        now = timezone.now()
        for index, (name, user_type, program, year, availability, gender, member_skills) in enumerate(
            DEMO_MEMBERS, start=1
        ):
            email = f"demo.member{index:02d}@skillbridge.example"
            profile = {
                "full_name": name,
                "user_type": user_type,
                "academic_program": program,
                "gender": gender,
                "admission_year": year,
                "npm": f"9900000{index:04d}" if user_type == User.UserType.STUDENT else None,
                "availability": availability,
                "is_active": True,
                "is_demo": True,
                "is_campus_verified": True,
                "verified_at": now,
            }
            user = User.objects.filter(email=email).first()
            if user is None:
                user = User.objects.create_user(email=email, password=None, **profile)
                self.stdout.write(f"Profil demo dibuat: {name}")
            elif user.is_demo:
                for field, value in profile.items():
                    setattr(user, field, value)
                user.save(update_fields=list(profile))
            else:
                raise CommandError(
                    f"Email demo {email} sudah dipakai akun non-demo; data tidak diubah."
                )

            demo_users[email] = user
            for skill_name in member_skills:
                UserSkill.objects.get_or_create(user=user, skill=skills[skill_name])

        for project_data in DEMO_PROJECTS:
            owner = demo_users[project_data["owner_email"]]
            project, _ = Project.objects.get_or_create(
                owner=owner,
                title=project_data["title"],
                defaults={
                    "description": project_data["description"],
                    "project_type": project_data["project_type"],
                    "deadline": timezone.localdate() + timedelta(days=45),
                    "status": Project.Status.PUBLISHED,
                },
            )
            role, _ = ProjectRole.objects.get_or_create(
                project=project,
                name=project_data["role_name"],
                defaults={"description": "Terbuka untuk anggota komunitas SkillBridge."},
            )
            role.required_skills.set(
                [skills[skill_name] for skill_name in project_data["skills"]]
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Data demo siap: {len(DEMO_MEMBERS)} profil dan "
                f"{len(DEMO_PROJECTS)} proyek contoh."
            )
        )
