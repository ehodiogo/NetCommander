from django.core.management.base import BaseCommand
from execucoes.models import Execucao
from django.db.models import Q


class Command(BaseCommand):
    help = "Marca como falha execuções presas em pendente/em_andamento"

    def handle(self, *args, **options):
        orfas = Execucao.objects.filter(
            Q(status='pendente') | Q(status='em_andamento')
        )
        total = orfas.count()
        if total == 0:
            self.stdout.write(self.style.SUCCESS("Nenhuma execução órfã encontrada."))
            return

        for ex in orfas:
            self.stdout.write(
                f"  Execução #{ex.id} ({ex.comando.nome}) - status={ex.status} "
                f"({ex.created_at})"
            )

        atualizadas = orfas.update(status='falha')
        self.stdout.write(
            self.style.SUCCESS(
                f"{atualizadas} execução(ões) órfã(s) marcada(s) como falha."
            )
        )
