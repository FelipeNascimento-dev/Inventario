# Generated manually for ExtracaoDiariaAuditoria

import django.db.models.deletion
from django.db import migrations, models

import inventario.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('inventario', '0043_alter_bipagem_estado'),
    ]

    operations = [
        migrations.CreateModel(
            name='ExtracaoDiariaAuditoria',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_referencia', models.DateField(verbose_name='Data de referência')),
                ('arquivo_pdf', models.FileField(upload_to=inventario.models._extracao_diaria_upload_to)),
                ('arquivo_csv', models.FileField(upload_to=inventario.models._extracao_diaria_upload_to)),
                ('total_seriais', models.PositiveIntegerField(default=0)),
                ('gerado_em', models.DateTimeField(auto_now_add=True)),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='extracoes_diarias', to='auth.group')),
            ],
            options={
                'verbose_name': 'Extração diária de auditoria',
                'verbose_name_plural': 'Extrações diárias de auditoria',
                'ordering': ['-data_referencia', 'group__name'],
            },
        ),
        migrations.AddConstraint(
            model_name='extracaodiariaauditoria',
            constraint=models.UniqueConstraint(fields=('group', 'data_referencia'), name='uniq_extracao_diaria_por_pa_data'),
        ),
    ]
