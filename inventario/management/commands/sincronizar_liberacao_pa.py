from django.core.management.base import BaseCommand

from inventario.services.liberacao_pa_service import sincronizar_liberado_pa


class Command(BaseCommand):
    help = (
        "Atualiza PontoAtendimentoInfo.liberado conforme janela do cronograma. "
        "Agendar a cada 1–5 minutos no servidor (cron) para refletir no admin."
    )

    def handle(self, *args, **options):
        resultado = sincronizar_liberado_pa()

        if resultado["atualizados"]:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sincronização em {resultado['agora']:%d/%m/%Y %H:%M}: "
                    f"{len(resultado['atualizados'])} PA(s) alterada(s)."
                )
            )
            for item in resultado["atualizados"]:
                estado = "LIBERADO" if item["liberado"] else "BLOQUEADO"
                self.stdout.write(f"  - {item['grupo']}: {estado}")
        else:
            self.stdout.write("Nenhuma alteração necessária.")
