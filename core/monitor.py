import logging
from concurrent.futures import ThreadPoolExecutor

from core.executor import MAX_WORKERS
from core.utils import PORTA_SSH_PADRAO, maquina_esta_online, scan_arp

logger = logging.getLogger(__name__)


def _ip_da_maquina(maquina, arp_table):
    mac = maquina.mac_address.lower().replace('-', ':')
    return arp_table.get(mac) or maquina.ultimo_ip


def _verificar_maquina(maquina, ip):
    if not ip:
        return {
            "id": maquina.id,
            "maquina": maquina.nome,
            "ip": "",
            "online": False,
            "motivo": "Sem IP conhecido (nunca localizada na rede).",
        }

    online, _ttl = maquina_esta_online(ip, maquina.porta_ssh or PORTA_SSH_PADRAO)
    return {
        "id": maquina.id,
        "maquina": maquina.nome,
        "ip": ip,
        "online": online,
        "motivo": "" if online else "Sem resposta de ping nem da porta SSH.",
    }


def verificar_sala(sala):
    """Verifica rapidamente quais máquinas da sala estão online.

    Usa o ARP cache para descobrir IPs ainda não cadastrados e faz o
    check em paralelo para que uma sala inteira seja verificada em
    poucos segundos.
    """
    maquinas = list(sala.maquinas.all())
    if not maquinas:
        return []

    arp_table = scan_arp()
    alvos = [(m, _ip_da_maquina(m, arp_table)) for m in maquinas]

    with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(alvos))) as pool:
        resultados = list(pool.map(lambda args: _verificar_maquina(*args), alvos))

    online = sum(1 for r in resultados if r["online"])
    logger.info(
        "Monitor: sala '%s' com %d/%d máquinas online",
        sala.nome, online, len(resultados),
    )
    return resultados
