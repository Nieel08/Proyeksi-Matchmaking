from datetime import date

from django import forms
from django.forms import inlineformset_factory

from accounts.models import Project, ProjectRole


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["title", "project_type", "description", "deadline"]
        labels = {"title": "Judul", "project_type": "Tipe", "description": "Deskripsi",
                  "deadline": "Deadline"}
        widgets = {
            "deadline": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deadline"].required = True
        self.fields["description"].required = True

    def clean_deadline(self):
        deadline = self.cleaned_data["deadline"]
        if deadline < date.today():
            raise forms.ValidationError("Deadline tidak boleh sebelum hari ini.")
        return deadline


class RoleForm(forms.ModelForm):
    class Meta:
        model = ProjectRole
        fields = ["name", "slots_needed", "required_skills"]
        labels = {"name": "Nama peran", "slots_needed": "Jumlah dibutuhkan",
                  "required_skills": "Skill yang dibutuhkan"}
        widgets = {"required_skills": forms.CheckboxSelectMultiple}

    def clean_slots_needed(self):
        n = self.cleaned_data["slots_needed"]
        if n < 1:
            raise forms.ValidationError("Minimal 1 orang.")
        return n


RoleFormSet = inlineformset_factory(
    Project, ProjectRole, form=RoleForm, extra=1, can_delete=True
)
