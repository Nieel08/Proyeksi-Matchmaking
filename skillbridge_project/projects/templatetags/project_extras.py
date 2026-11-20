from django import template

register = template.Library()


@register.filter
def owner_label(user):
    """Label pembuat proyek. Memakai field `role` bila nanti ditambahkan ke User;
    sampai saat itu tampil nama lengkap."""
    if user.is_superuser or user.is_staff:
        return "Admin"
    role = str(getattr(user, "role", "")).lower()
    if role == "dosen":
        return "Dosen"
    if role == "mahasiswa":
        return "Mahasiswa"
    return user.full_name
