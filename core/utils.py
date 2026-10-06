import logging
import platform
import re
import socket
import subprocess

from decouple import config

logger = logging.getLogger(__name__)

PORTA_SSH_PADRAO = 22
PING_TIMEOUT_MS = config('PING_TIMEOUT_MS', default=1000, cast=int)
PING_TIMEOUT_SEGUNDOS = config('PING_TIMEOUT_SEGUNDOS', default=1, cast=int)
TIMEOUT_PORTA_SSH_SEGUNDOS = config(
    'TIMEOUT_PORTA_SSH_SEGUNDOS', default=2, cast=int
)
MARGEM_TIMEOUT_PING = 4


def _sistema(sistema=None):
    return (sistema or platform.system()).lower()


def _comando_ping(ip, sistema):
    """Monta o ping com as flags corretas da plataforma do servidor."""
    if sistema == "windows":
        return ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS), ip]
    return ["ping", "-c", "1", "-W", str(PING_TIMEOUT_SEGUNDOS), ip]


def ping_responde(ip, sistema=None):
    """Executa ping e retorna (online, ttl)."""
    sistema = _sistema(sistema)
    espera = (
        PING_TIMEOUT_MS / 1000
        if sistema == "windows"
        else PING_TIMEOUT_SEGUNDOS
    )

    try:
        resultado = subprocess.run(
            _comando_ping(ip, sistema),
            capture_output=True,
            text=True,
            timeout=espera + MARGEM_TIMEOUT_PING,
        )
    except subprocess.TimeoutExpired:
        logger.warning("Timeout no ping para %s", ip)
        return False, None
    except OSError as e:
        logger.warning("Falha ao executar ping para %s: %s", ip, e)
        return False, None

    if resultado.returncode != 0:
        logger.debug("Ping sem resposta para %s (código %s)", ip, resultado.returncode)
        return False, None

    ttl_match = re.search(r'[Tt][Tt][Ll][= ](\d+)', resultado.stdout)
    ttl = int(ttl_match.group(1)) if ttl_match else None
    return True, ttl


def porta_ssh_responde(ip, porta=PORTA_SSH_PADRAO, timeout=TIMEOUT_PORTA_SSH_SEGUNDOS):
    """Testa se a porta SSH está aberta."""
    porta = porta or PORTA_SSH_PADRAO

    try:
        with socket.create_connection((ip, porta), timeout=timeout):
            logger.info("Porta SSH %s respondeu em %s", porta, ip)
            return True
    except OSError as e:
        logger.info("Porta SSH %s não respondeu em %s: %s", porta, ip, e)
        return False


def maquina_esta_online(ip, porta_ssh=PORTA_SSH_PADRAO, sistema=None):
    """Retorna (online, ttl) testando ping e, no Windows, a porta SSH.

    No Windows o ICMP é normalmente bloqueado pelo firewall, mesmo com o
    OpenSSH liberado. Quando o ping falha, a porta SSH aberta é prova
    suficiente de que a máquina está alcançável.
    """
    sistema = _sistema(sistema)

    online, ttl = ping_responde(ip, sistema=sistema)
    if online:
        return True, ttl

    if sistema == "windows" and porta_ssh_responde(ip, porta_ssh):
        logger.info(
            "%s considerado online via porta SSH %s (ICMP bloqueado)", ip, porta_ssh
        )
        return True, None

    return False, None


def atualizar_cache_rede(broadcast="255.255.255.255"):
    sistema = platform.system().lower()
    if sistema == "windows":
        subprocess.run(
            ["ping", "-n", "1", "-w", "100", broadcast],
            capture_output=True
        )
    else:
        subprocess.run(
            ["ping", "-b", "-c", "1", broadcast],
            capture_output=True, timeout=2
        )


def scan_arp():
    sistema = platform.system().lower()

    try:
        if sistema == "windows":
            output = subprocess.check_output(
                "arp -a", shell=True, encoding='cp1252', errors='replace'
            )
        else:
            output = subprocess.check_output(
                ["arp", "-a"], encoding='utf-8', errors='replace'
            )
    except Exception as e:
        logger.warning("Erro ao executar arp -a: %s", e)
        return {}

    result = {}
    lines = output.splitlines()
    for line in lines:
        ip_match = re.search(
            r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line
        )
        mac_match = re.search(
            r'([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-]'
            r'[0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})',
            line
        )

        if ip_match and mac_match:
            mac = mac_match.group(1).lower().replace('-', ':')
            ip = ip_match.group(1)
            result[mac] = ip

    logger.debug("ARP scan encontrou %d máquinas", len(result))
    return result
