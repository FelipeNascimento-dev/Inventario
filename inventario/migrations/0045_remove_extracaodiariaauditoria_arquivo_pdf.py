# Generated manually

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0044_extracao_diaria_auditoria'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='extracaodiariaauditoria',
            name='arquivo_pdf',
        ),
    ]
