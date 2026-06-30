from datetime import date, time

from django.db import migrations, models
import django.db.models.deletion


CRONOGRAMA_INICIAL = [
    ("CD PAYTEC BARUERI", date(2026, 7, 6), date(2026, 7, 10), time(6, 0), time(16, 0)),
    ("Lab. Gertec", date(2026, 7, 6), date(2026, 7, 6), time(8, 0), time(18, 0)),
    ("Lab. Tectoy/PAX", date(2026, 7, 7), date(2026, 7, 8), time(7, 0), time(17, 0)),
    ("Lab. Ogea", date(2026, 7, 10), date(2026, 7, 10), time(7, 0), time(16, 0)),
    ("MT- Oires Cuiabá", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("SP - MOBYPOINT - ZONA LESTE", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("AG.2307_ CALHAU SÃO LUIS_CORNER", date(2026, 7, 6), date(2026, 7, 7), time(9, 0), time(16, 0)),
    ("SP - VIG CAMPINAS", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("SE - FP LOGISTICA", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
    ("SP - PAYTEC FILIAL", date(2026, 7, 11), date(2026, 7, 11), time(7, 0), time(17, 0)),
]


def popular_cronograma(apps, schema_editor):
    Cronograma = apps.get_model("inventario", "CronogramaInventarioLocal")
    for nome, inicio, fim, h_ini, h_fim in CRONOGRAMA_INICIAL:
        Cronograma.objects.get_or_create(
            nome_local=nome,
            defaults={
                "data_inicio": inicio,
                "data_fim": fim,
                "horario_inicio": h_ini,
                "horario_fim": h_fim,
                "ativo": True,
            },
        )


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("inventario", "0046_bipagem_indexes"),
    ]

    operations = [
        migrations.CreateModel(
            name="CronogramaInventarioLocal",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome_local", models.CharField(max_length=255, verbose_name="Local")),
                (
                    "data_inicio",
                    models.DateField(verbose_name="Data início"),
                ),
                ("data_fim", models.DateField(verbose_name="Data fim")),
                ("horario_inicio", models.TimeField(verbose_name="Horário início")),
                ("horario_fim", models.TimeField(verbose_name="Horário fim")),
                ("ativo", models.BooleanField(default=True)),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        help_text="Vincule ao grupo INV_PA correspondente. Se vazio, tenta resolver pelo nome do local.",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="cronogramas_inventario",
                        to="auth.group",
                        verbose_name="Grupo (PA)",
                    ),
                ),
            ],
            options={
                "verbose_name": "Cronograma de inventário por local",
                "verbose_name_plural": "Cronogramas de inventário por local",
                "ordering": ["data_inicio", "nome_local"],
            },
        ),
        migrations.RunPython(popular_cronograma, migrations.RunPython.noop),
    ]
