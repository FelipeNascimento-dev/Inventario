from django.db import migrations


def provisionar_grupos_pa(apps, schema_editor):
    from inventario.services.locais_inventario_service import provisionar_todos_locais_cronograma
    from inventario.services.liberacao_pa_service import sincronizar_liberado_pa

    provisionar_todos_locais_cronograma()
    sincronizar_liberado_pa()


class Migration(migrations.Migration):

    dependencies = [
        ("inventario", "0048_remove_bipagem_bipagem_nrserie_idx_and_more"),
    ]

    operations = [
        migrations.RunPython(provisionar_grupos_pa, migrations.RunPython.noop),
    ]
