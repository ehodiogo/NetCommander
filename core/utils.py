import logging
import platform
import re
import subprocess

logger = logging.getLogger(__name__)


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
