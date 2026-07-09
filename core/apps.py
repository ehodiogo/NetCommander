import logging
import warnings

from django.apps import AppConfig
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        try:
            from execucoes.models import Execucao

            with warnings.catch_warnings():
                warnings.filterwarnings(
                    'ignore',
                    message='Accessing the database during app initialization',
                )
                orfas = Execucao.objects.filter(
                    status__in=['pendente', 'em_andamento']
                )
                total = orfas.count()
                if total:
                    for ex in orfas:
                        logger.warning(
                            "Execução órfã no startup: #%s (%s) - status=%s - criada em %s",
                            ex.id, ex.comando.nome, ex.status, ex.created_at,
                        )
                    orfas.update(status='falha')
                    logger.info("%s execução(ões) órfã(s) marcada(s) como falha no startup.", total)
        except OperationalError:
            pass
        except Exception:
            logger.exception("Erro ao limpar execuções órfãs no startup")
