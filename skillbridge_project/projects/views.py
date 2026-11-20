from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Project

from .forms import ProjectForm, RoleFormSet


def _active_roles(formset):
    """Peran yang diisi dan tidak ditandai hapus."""
    return [f for f in formset.forms if f.cleaned_data and not f.cleaned_data.get("DELETE")]


def _can_publish(project):
    """Syarat publikasi: minimal 1 peran dan ada skill di minimal 1 peran."""
    roles = project.roles.all()
    return roles.exists() and any(r.required_skills.exists() for r in roles)


@login_required
def project_list(request):
    projects = (
        Project.objects.filter(status=Project.Status.PUBLISHED)
        .select_related("owner")
        .prefetch_related("roles")
    )
    tipe = request.GET.get("tipe")
    if tipe in Project.ProjectType.values:
        projects = projects.filter(project_type=tipe)
    page = Paginator(projects, 9).get_page(request.GET.get("page"))
    return render(request, "projects/project_list.html", {
        "page": page, "types": Project.ProjectType.choices, "tipe": tipe,
    })


@login_required
def my_projects(request):
    projects = request.user.owned_projects.all()
    return render(request, "projects/my_projects.html", {"projects": projects})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(
        Project.objects.select_related("owner").prefetch_related("roles__required_skills"),
        pk=pk,
    )
    if project.status != Project.Status.PUBLISHED and project.owner != request.user:
        raise Http404
    return render(request, "projects/project_detail.html", {
        "project": project, "is_owner": project.owner == request.user,
    })


@login_required
def project_form(request, pk=None):
    """Satu view untuk BUAT (pk=None) dan EDIT (pk diisi)."""
    project = get_object_or_404(Project, pk=pk, owner=request.user) if pk else None

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        formset = RoleFormSet(request.POST, instance=project)
        if form.is_valid() and formset.is_valid():
            roles = _active_roles(formset)
            publish = request.POST.get("action") == "publish"
            if not roles:
                messages.error(request, "Tambahkan minimal 1 peran yang dibutuhkan.")
            elif publish and not any(f.cleaned_data.get("required_skills") for f in roles):
                messages.error(request, "Untuk dipublikasikan, minimal 1 peran harus punya skill.")
            else:
                obj = form.save(commit=False)
                if project is None:
                    obj.owner = request.user
                    obj.status = Project.Status.DRAFT
                if publish:
                    obj.status = Project.Status.PUBLISHED
                obj.save()
                formset.instance = obj
                formset.save()
                messages.success(
                    request,
                    "Proyek dipublikasikan." if publish else "Proyek disimpan sebagai draft.",
                )
                return redirect("projects:detail", pk=obj.pk)
    else:
        form = ProjectForm(instance=project)
        formset = RoleFormSet(instance=project)

    return render(request, "projects/project_form.html", {
        "form": form, "formset": formset, "project": project,
    })


@login_required
@require_POST
def project_publish(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if _can_publish(project):
        project.status = Project.Status.PUBLISHED
        project.save()
        messages.success(request, "Proyek dipublikasikan.")
    else:
        messages.error(request, "Lengkapi dulu minimal 1 peran beserta skill-nya.")
    return redirect("projects:detail", pk=pk)


@login_required
@require_POST
def project_close(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.status = Project.Status.CLOSED
    project.save()
    messages.success(request, "Proyek ditutup.")
    return redirect("projects:detail", pk=pk)


@login_required
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    if request.method == "POST":
        project.delete()
        messages.success(request, "Proyek dihapus.")
        return redirect("projects:mine")
    return render(request, "projects/project_confirm_delete.html", {"project": project})
