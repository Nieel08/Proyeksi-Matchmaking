from django.contrib.auth.management.commands.createsuperuser import (
    Command as DjangoCreateSuperuserCommand,
)


class Command(DjangoCreateSuperuserCommand):
    def get_input_data(self, field, message, default=None):
        if field.name == "gender":
            choices = ", ".join(
                f"{value} ({label})" for value, label in field.choices
            )
            self.stdout.write(
                f"Pilihan gender yang valid: {choices}. "
                "Masukkan kode, bukan istilah atau label lain."
            )
        return super().get_input_data(field, message, default)
