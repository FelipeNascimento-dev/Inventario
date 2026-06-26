from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0041_remove_bipagem_estado'),
    ]

    operations = [
        migrations.AddField(
            model_name='bipagem',
            name='estado',
            field=models.CharField(
                blank=True,
                choices=[
                    ('GOOD', 'GOOD'),
                    ('BAD', 'BAD'),
                    ('OBSOLETO', 'OBSOLETO'),
                    ('TRIAGEM', 'TRIAGEM'),
                ],
                max_length=100,
                null=True,
            ),
        ),
    ]
