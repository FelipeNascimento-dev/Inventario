from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0045_remove_extracaodiariaauditoria_arquivo_pdf'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='bipagem',
            index=models.Index(fields=['nrserie'], name='bipagem_nrserie_idx'),
        ),
        migrations.AddIndex(
            model_name='bipagem',
            index=models.Index(
                fields=['id_lote', 'nrserie'],
                name='bipagem_lote_serial_idx',
            ),
        ),
    ]
