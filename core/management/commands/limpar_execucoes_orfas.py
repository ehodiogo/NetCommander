from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q

from execucoes.models import Execucao
from core.executor import EXECUCAO_TIMEOUT


class Command(BaseCommand):
    help = "Marca como falha execuções presas em pendente/em_andamento há mais tempo que o limiar"

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=EXECUCAO_TIMEOUT,
            help=f'Tempo em segundos para considerar uma execução como órfã (padrão: EXECUCAO_TIMEOUT={EXECUCAO_TIMEOUT})',
        )

    def handle(self, *args, **options):
        timeout = options['timeout']
        limiar = timezone.now() - timedelta(seconds=timeout)

        orfas = Execucao.objects.filter(
            Q(status='pendente') | Q(status='em_andamento'),
            updated_at__lt=limiar,
        )

        total = orfas.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nenhuma execução órfã encontrada."))
            return

        for ex in orfas:
            idade = timezone.now() - ex.updated_at
            minutos = int(idade.total_seconds() // 60)
            segundos = int(idade.total_seconds() % 60)
            idade_str = f"{minutos}m {segundos}s" if minutos else f"{segundos}s"
            self.stdout.write(
                f"  Execução #{ex.id} ({ex.comando.nome}) - status={ex.status} "
                f"(criada em {ex.created_at}, última atualização há {idade_str})"
            )

        atualizadas = orfas.update(status='falha')
        self.stdout.write(
            self.style.SUCCESS(
                f"{atualizadas} execução(ões) órfã(s) marcada(s) como falha."
            )
        )
