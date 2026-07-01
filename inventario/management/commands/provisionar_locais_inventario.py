from django.core.management.base import BaseCommand

from inventario.services.locais_inventario_service import provisionar_todos_locais_cronograma


class Command(BaseCommand):
    help = (
        "Cria ou atualiza grupos INV_PA_, PontoAtendimentoInfo e vínculos "
        "com CronogramaInventarioLocal a partir da tabela de locais."
    )

    def handle(self, *args, **options):
        resultados = provisionar_todos_locais_cronograma()

        criados = sum(1 for item in resultados if item["grupo_criado"])
        self.stdout.write(
            self.style.SUCCESS(
                f"Provisionamento concluído: {len(resultados)} locais "
                f"({criados} grupos novos)."
            )
        )

        for item in resultados:
            status = "NOVO" if item["grupo_criado"] else "ok"
            self.stdout.write(f"  [{status}] {item['grupo']} -> cronograma #{item['cronograma_id']}")
