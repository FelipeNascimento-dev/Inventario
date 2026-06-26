from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from inventario.services.extracao_auditoria_service import (
    gerar_todas_extracoes_diarias,
    horario_extracao_auditoria_label,
)


class Command(BaseCommand):
    help = (
        "Gera extrações CSV diárias de todas as PAs para usuários de auditoria. "
        f"Agendar para {horario_extracao_auditoria_label()} (America/Sao_Paulo)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--data",
            help="Data de referência no formato AAAA-MM-DD (padrão: hoje em America/Sao_Paulo).",
        )

    def handle(self, *args, **options):
        data_referencia = None
        if options.get("data"):
            data_referencia = datetime.strptime(options["data"], "%Y-%m-%d").date()

        resultado = gerar_todas_extracoes_diarias(data_referencia)

        self.stdout.write(
            self.style.SUCCESS(
                f"Extrações geradas para {resultado['data_referencia']}: "
                f"{len(resultado['geradas'])} PAs."
            )
        )

        for item in resultado["geradas"]:
            self.stdout.write(f"  - {item['pa']}: {item['total_seriais']} seriais")

        for erro in resultado["erros"]:
            self.stdout.write(self.style.ERROR(f"  ERRO {erro['pa']}: {erro['erro']}"))

        if resultado["erros"]:
            raise SystemExit(1)
