# Django
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("assets", "0003_alter_general_options"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="general",
            options={
                "default_permissions": (),
                "managed": False,
                "permissions": [
                    ("basic_access", "Can access this app"),
                    ("corporation_access", "Can access own corporation assets"),
                    ("admin_access", "Can access all assets."),
                    ("manage_corporation", "Can add corporation assets"),
                    ("manage_requests", "Can manage requests"),
                ],
                "verbose_name": "AA-Assets",
                "verbose_name_plural": "AA-Assets",
            },
        ),
    ]
