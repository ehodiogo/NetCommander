import ipaddress
import logging
import platform
import re
import socket
import subprocess
import threading
import time
from decouple import config
import paramiko

logger = logging.getLogger(__name__)

NCC_PASSWORD = config('NCC_ADMIN_PASSWORD', default='senha_padrao')


def _validar_mac(mac):
    if not mac or len(mac) > 17:
        return False
    return bool(re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac))


def _ping_responde(ip):
    sistema = platform.system().lower()

    if sistema == "windows":
        comando = ["ping", "-n", "1", "-w", "1000", ip]
    else:
        comando = ["ping", "-c", "1", "-W", "1", ip]

    try:
        resultado = subprocess.run(comando, capture_output=True, text=True, timeout=5)
        return resultado.returncode == 0
    except subprocess.TimeoutExpired:
        logger.warning("Timeout no ping para %s", ip)
        return False


def _detectar_broadcasts():
    sistema = platform.system().lower()
    broadcasts = ["255.255.255.255"]

    try:
        if sistema == "windows":
            output = subprocess.check_output(
                "ipconfig", shell=True, encoding='cp1252', errors='replace'
            )
            ips = re.findall(
                r'(?:IPv4|IP|Endere[çc]o).*:\s*(\d+\.\d+\.\d+\.\d+)',
                output, re.IGNORECASE
            )
            masks = re.findall(
                r'(?:Mask|Masc|M[áa]scara).*:\s*(\d+\.\d+\.\d+\.\d+)',
                output, re.IGNORECASE
            )
            for ip_str, mask_str in zip(ips, masks):
                try:
                    ip = ipaddress.IPv4Address(ip_str.strip())
                    mask = ipaddress.IPv4Address(mask_str.strip())
                    network = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
                    bcast = str(network.broadcast_address)
                    if bcast not in broadcasts:
                        broadcasts.append(bcast)
                        logger.debug(
                            "Broadcast detectado: %s (IP: %s, Máscara: %s)",
                            bcast, ip, mask
                        )
                except ValueError:
                    continue
        else:
            output = subprocess.check_output(
                ["ip", "addr"], encoding='utf-8', errors='replace'
            )
            for match in re.finditer(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', output):
                try:
                    network = ipaddress.IPv4Network(
                        f"{match.group(1)}/{match.group(2)}", strict=False
                    )
                    bcast = str(network.broadcast_address)
                    if bcast not in broadcasts:
                        broadcasts.append(bcast)
                        logger.debug("Broadcast detectado: %s", bcast)
                except ValueError:
                    continue
    except Exception as e:
        logger.warning("Erro ao detectar broadcasts: %s", e)

    logger.info("Broadcasts disponíveis: %s", broadcasts)
    return broadcasts


def enviar_wol(mac, ip=None, porta=9):
    if not _validar_mac(mac):
        logger.error("MAC inválido para WoL: %s", mac)
        return False, f"MAC inválido: {mac}"

    mac_limpo = mac.replace("-", ":").replace(".", "").lower().replace(":", "")
    try:
        pacote = bytes.fromhex("ff" * 6 + mac_limpo * 16)
    except ValueError as e:
        logger.error("Erro ao construir pacote WoL para MAC %s: %s", mac, e)
        return False, f"Erro ao construir pacote mágico: {e}"

    broadcasts = _detectar_broadcasts()
    logger.info(
        "Enviando WoL para MAC %s (IP: %s) - broadcasts: %s",
        mac, ip or "N/A", broadcasts
    )

    enviado = False
    for destino in broadcasts:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(2)
                sock.sendto(pacote, (destino, porta))
                logger.debug("Pacote WoL enviado para broadcast %s:%s", destino, porta)
                enviado = True
        except Exception as e:
            logger.warning("Falha ao enviar WoL para broadcast %s: %s", destino, e)

    if not enviado:
        logger.error("Nenhum broadcast funcionou para WoL MAC %s", mac)
        return False, "Falha ao enviar pacote WoL para todos os broadcasts."

    logger.info("WoL concluído para MAC %s", mac)
    return True, None


def garantir_maquina_ligada(ip, mac, tentativas=12, intervalo=5):
    logger.info("Verificando se %s (%s) está online...", ip, mac)
    if _ping_responde(ip):
        logger.info("Máquina %s já está online", ip)
        return True, None, False

    logger.info("Máquina %s offline. Enviando WoL...", ip)
    sucesso_wol, erro_wol = enviar_wol(mac, ip)
    if not sucesso_wol:
        logger.error("Falha no WoL para %s (%s): %s", mac, ip, erro_wol)
        return False, f"Falha no WoL: {erro_wol}", False

    for i in range(tentativas):
        logger.debug(
            "Aguardando %s ficar online... (tentativa %d/%d)",
            ip, i + 1, tentativas
        )
        time.sleep(intervalo)
        if _ping_responde(ip):
            logger.info("Máquina %s está online após WoL", ip)
            return True, None, True

    return (
        False,
        f"Máquina não respondeu ao ping após Wake on LAN em {tentativas * intervalo}s.",
        True,
    )


def _executar_ssh(ip, comando, timeout=10):
    """Executa um comando via SSH com paramiko."""
    logger.info("Conectando via SSH em %s", ip)
    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        cliente.connect(
            hostname=ip,
            username='ncc',
            password=NCC_PASSWORD,
            timeout=timeout,
            allow_agent=False,
            look_for_keys=False,
        )

        stdin, stdout, stderr = cliente.exec_command(comando, timeout=timeout)
        saida = stdout.read().decode('utf-8', errors='replace').strip()
        erro = stderr.read().decode('utf-8', errors='replace').strip()

        logger.debug("SSH %s executado (stdout: %dB, stderr: %dB)", ip, len(saida), len(erro))

        if erro:
            logger.warning("SSH %s stderr: %s", ip, erro[:300])

        return saida or erro or "Comando executado sem saída."

    except paramiko.AuthenticationException:
        logger.error("Falha de autenticação SSH em %s", ip)
        raise Exception(f"Falha de autenticação SSH em {ip}")
    except OSError as e:
        logger.error("Erro de conexão SSH em %s: %s", ip, e)
        raise Exception(f"Máquina {ip} offline ou inacessível: {e}")
    except Exception as e:
        logger.error("Erro SSH em %s: %s", ip, e)
        raise
    finally:
        try:
            cliente.close()
        except Exception:
            pass


def executar_linux(ip, comando):
    return _executar_ssh(ip, comando)


def executar_windows(ip, comando):
    return _executar_ssh(ip, comando)


def detectar_os(ip):
    logger.info("Detectando SO em %s", ip)
    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        cliente.connect(
            hostname=ip,
            username='ncc',
            password=NCC_PASSWORD,
            timeout=5,
            allow_agent=False,
            look_for_keys=False,
        )
        return "debian"
    except Exception:
        return "windows"
    finally:
        try:
            cliente.close()
        except Exception:
            pass


def worker(maquina, comando, arp_table, resultados, lock):
    mac_banco = maquina.mac_address.lower().replace('-', ':')

    ip = arp_table.get(mac_banco)

    if not ip:
        ip = maquina.ultimo_ip
        usa_fallback = True
    else:
        usa_fallback = False

    if not ip:
        logger.warning("Máquina %s não localizada na rede (ARP/DB)", maquina.nome)
        with lock:
            resultados.append({
                "maquina": maquina.nome,
                "status": "offline",
                "ip": "Nenhum",
                "os": "N/A",
                "output": "Máquina não localizada na rede (ARP/DB)."
            })
        return

    try:
        online, mensagem, wol_enviado = garantir_maquina_ligada(ip, mac_banco)
    except Exception as e:
        logger.exception(
            "Erro ao garantir máquina ligada %s (%s): %s",
            maquina.nome, ip, e
        )
        with lock:
            resultados.append({
                "maquina": maquina.nome,
                "ip": ip,
                "os": "N/A",
                "status": "offline",
                "output": f"Erro ao verificar disponibilidade: {e}",
            })
        return

    if not online:
        logger.warning("Máquina %s (%s) offline: %s", maquina.nome, ip, mensagem)
        with lock:
            resultados.append({
                "maquina": maquina.nome,
                "ip": ip,
                "os": "N/A",
                "status": "offline",
                "output": mensagem,
            })
        return

    os_execucao = maquina.tipo_os
    if maquina.tipo_os == "dual":
        os_execucao = "debian" if wol_enviado else detectar_os(ip)

    try:
        if os_execucao == "debian":
            output = executar_linux(ip, comando.comando_linux)
        else:
            output = executar_windows(ip, comando.comando_windows)

        status = "sucesso"

        if ip != maquina.ultimo_ip:
            maquina.ultimo_ip = ip
            maquina.save()

    except Exception as e:
        output = f"Falha na conexão: {str(e)}"
        status = "erro"

    with lock:
        resultados.append({
            "maquina": maquina.nome,
            "ip": ip,
            "os": os_execucao,
            "status": status,
            "output": output
        })


def executar_em_paralelo(maquinas, comando, arp_table):
    threads = []
    resultados = []
    lock = threading.Lock()

    for maquina in maquinas:
        t = threading.Thread(
            target=worker,
            args=(maquina, comando, arp_table, resultados, lock)
        )
        t.start()
        threads.append(t)

    for t in threads:
        t.join()

    return resultados
