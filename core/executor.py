import ipaddress
import logging
import platform
import re
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from decouple import config
import paramiko

EXECUCAO_TIMEOUT = config('EXECUCAO_TIMEOUT', default=300, cast=int)

logger = logging.getLogger(__name__)

NCC_PASSWORD = config('NCC_ADMIN_PASSWORD', default='senha_padrao')
MAX_WORKERS = config('MAX_WORKERS', default=10, cast=int)
_ip_update_lock = threading.Lock()

GRUB_WINDOWS_ENTRY = "Windows Boot Manager"


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
        if resultado.returncode == 0:
            ttl_match = re.search(r'[Tt][Tt][Ll][= ](\d+)', resultado.stdout)
            ttl = int(ttl_match.group(1)) if ttl_match else None
            return True, ttl
        return False, None
    except subprocess.TimeoutExpired:
        logger.warning("Timeout no ping para %s", ip)
        return False, None


def detectar_os_por_ttl(ttl):
    if ttl is None:
        return "desconhecido"
    if 48 <= ttl <= 80:
        return "debian"
    elif 100 <= ttl <= 140:
        return "windows"
    return "desconhecido"


_broadcasts_cache = None

def _detectar_broadcasts():
    global _broadcasts_cache
    if _broadcasts_cache is not None:
        return _broadcasts_cache.copy()

    sistema = platform.system().lower()
    broadcasts = ["255.255.255.255"]

    try:
        if sistema == "windows":
            output = subprocess.check_output(
                "ipconfig", shell=True, encoding='cp1252', errors='replace',
                timeout=10
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
                ["ip", "addr"], encoding='utf-8', errors='replace',
                timeout=10
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

    _broadcasts_cache = broadcasts.copy()
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

    portas = [porta]
    if porta != 7:
        portas.append(7)

    enviado = False
    for destino in broadcasts:
        for p in portas:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    sock.settimeout(2)
                    sock.bind(('0.0.0.0', 0))
                    for tentativa in range(3):
                        sock.sendto(pacote, (destino, p))
                        logger.debug(
                            "Pacote WoL enviado para broadcast %s:%s "
                            "(tentativa %d/3)", destino, p, tentativa + 1
                        )
                        enviado = True
                        if tentativa < 2:
                            time.sleep(0.1)
            except Exception as e:
                logger.warning(
                    "Falha ao enviar WoL para broadcast %s:%s: %s",
                    destino, p, e
                )

    if not enviado:
        logger.error("Nenhum broadcast funcionou para WoL MAC %s", mac)
        return False, "Falha ao enviar pacote WoL para todos os broadcasts."

    logger.info("WoL concluído para MAC %s", mac)
    return True, None


def garantir_maquina_ligada(ip, mac, tentativas=12, intervalo=5):
    logger.info("Verificando se %s (%s) está online...", ip, mac)
    online, ttl = _ping_responde(ip)
    if online:
        logger.info("Máquina %s já está online (TTL: %s)", ip, ttl)
        return True, None, False, ttl

    logger.info("Máquina %s offline. Enviando WoL...", ip)
    sucesso_wol, erro_wol = enviar_wol(mac, ip)
    if not sucesso_wol:
        logger.error("Falha no WoL para %s (%s): %s", mac, ip, erro_wol)
        return False, f"Falha no WoL: {erro_wol}", False, None

    for i in range(tentativas):
        logger.debug(
            "Aguardando %s ficar online... (tentativa %d/%d)",
            ip, i + 1, tentativas
        )
        time.sleep(intervalo)
        online, ttl = _ping_responde(ip)
        if online:
            logger.info("Máquina %s está online após WoL (TTL: %s)", ip, ttl)
            return True, None, True, ttl

    return (
        False,
        f"Máquina não respondeu ao ping após Wake on LAN em {tentativas * intervalo}s.",
        True,
        None,
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


def _reboot_para_windows(ip, tentativas_max=18, intervalo=10):
    logger.info("Preparando reboot de %s para Windows...", ip)
    try:
        _executar_ssh(
            ip,
            f"sudo grub-reboot \"{GRUB_WINDOWS_ENTRY}\" && sudo reboot",
            timeout=10
        )
    except Exception as e:
        logger.error("Falha ao configurar reboot para Windows em %s: %s", ip, e)
        return False, None

    logger.info("Aguardando %s desligar (reboot)...", ip)
    for _ in range(10):
        time.sleep(3)
        online, _ = _ping_responde(ip)
        if not online:
            logger.info("%s está offline (reiniciando)", ip)
            break
    else:
        logger.warning("%s não desligou após reboot", ip)
        return False, None

    logger.info("Aguardando %s voltar online (Windows)...", ip)
    for i in range(tentativas_max):
        time.sleep(intervalo)
        online, ttl = _ping_responde(ip)
        if online:
            logger.info("%s voltou online (TTL: %s) — Windows detectado", ip, ttl)
            return True, ttl

    logger.error("%s não voltou online após reboot", ip)
    return False, None


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


def _atualizar_progresso(resultado_id, progresso, status=None, output=None):
    from execucoes.models import ResultadoMaquina as ResModel
    kwargs = {"progresso": progresso}
    if status is not None:
        kwargs["status"] = status
    if output is not None:
        kwargs["output"] = output
    ResModel.objects.filter(id=resultado_id).update(**kwargs)


def worker(maquina, comando, arp_table, resultado_id=None, os_alvo=None):
    mac_banco = maquina.mac_address.lower().replace('-', ':')

    if resultado_id:
        _atualizar_progresso(resultado_id, 'verificando_rede')

    ip = arp_table.get(mac_banco)

    if not ip:
        ip = maquina.ultimo_ip

    if not ip:
        logger.warning("Máquina %s não localizada na rede (ARP/DB)", maquina.nome)
        if resultado_id:
            _atualizar_progresso(resultado_id, 'erro', status='offline',
                                 output="Máquina não localizada na rede (ARP/DB).")
        return {
            "maquina": maquina.nome,
            "status": "offline",
            "ip": "Nenhum",
            "os": "N/A",
            "output": "Máquina não localizada na rede (ARP/DB)."
        }

    if resultado_id:
        _atualizar_progresso(resultado_id, 'aguardando_wol')

    try:
        online, mensagem, wol_enviado, ttl = garantir_maquina_ligada(ip, mac_banco)
    except Exception as e:
        logger.exception(
            "Erro ao garantir máquina ligada %s (%s): %s",
            maquina.nome, ip, e
        )
        if resultado_id:
            _atualizar_progresso(resultado_id, 'erro', status='offline',
                                 output=f"Erro ao verificar disponibilidade: {e}")
        return {
            "maquina": maquina.nome,
            "ip": ip,
            "os": "N/A",
            "status": "offline",
            "output": f"Erro ao verificar disponibilidade: {e}",
        }

    if not online:
        logger.warning("Máquina %s (%s) offline: %s", maquina.nome, ip, mensagem)
        if resultado_id:
            _atualizar_progresso(resultado_id, 'erro', status='offline', output=mensagem)
        return {
            "maquina": maquina.nome,
            "ip": ip,
            "os": "N/A",
            "status": "offline",
            "output": mensagem,
        }

    if resultado_id:
        _atualizar_progresso(resultado_id, 'conectando_ssh')

    os_execucao = maquina.tipo_os
    os_detectado = None

    if maquina.tipo_os == "dual":
        os_atual = detectar_os_por_ttl(ttl) if ttl is not None else "desconhecido"
        os_detectado = os_atual

        if os_alvo is not None:
            os_execucao = os_alvo
        elif comando.comando_windows and not comando.comando_linux:
            os_execucao = "windows"
        elif comando.comando_linux and not comando.comando_windows:
            os_execucao = "debian"
        else:
            os_execucao = os_atual

        if os_execucao == "windows" and os_atual == "debian":
            if resultado_id:
                _atualizar_progresso(
                    resultado_id, 'conectando_ssh',
                    output="Preparando boot para Windows..."
                )
            sucesso, novo_ttl = _reboot_para_windows(ip)
            if not sucesso:
                if resultado_id:
                    _atualizar_progresso(
                        resultado_id, 'erro', status='erro',
                        output="Falha ao reiniciar para Windows."
                    )
                return {
                    "maquina": maquina.nome,
                    "ip": ip,
                    "os": "N/A",
                    "os_detectado": os_detectado,
                    "status": "erro",
                    "output": "Falha ao reiniciar máquina para Windows.",
                }
            ttl = novo_ttl

    elif ttl is not None:
        os_detectado = detectar_os_por_ttl(ttl)

    if resultado_id:
        _atualizar_progresso(resultado_id, 'executando')

    try:
        if os_execucao == "debian":
            output = executar_linux(ip, comando.comando_linux)
        else:
            output = executar_windows(ip, comando.comando_windows)

        status = "sucesso"

        with _ip_update_lock:
            maquina_atualizada = type(maquina).objects.get(pk=maquina.pk)
            if ip != maquina_atualizada.ultimo_ip:
                maquina_atualizada.ultimo_ip = ip
                maquina_atualizada.save()

        if resultado_id:
            from execucoes.models import ResultadoMaquina as ResModel
            ResModel.objects.filter(id=resultado_id).update(os_detectado=os_detectado)

    except Exception as e:
        output = f"Falha na conexão: {str(e)}"
        status = "erro"

    if resultado_id:
        _atualizar_progresso(resultado_id, 'concluido', status=status, output=output)

    return {
        "maquina": maquina.nome,
        "ip": ip,
        "os": os_execucao,
        "os_detectado": os_detectado,
        "status": status,
        "output": output
    }


def executar_em_paralelo(maquinas, comando, arp_table, execucao=None, timeout=None, os_alvo=None):
    resultados = []
    futures = []

    resultados_ids = []
    if execucao is not None:
        from execucoes.models import ResultadoMaquina as ResModel
        for m in maquinas:
            r = ResModel.objects.create(
                execucao=execucao,
                maquina=m,
                status='pendente',
                progresso='pendente',
            )
            resultados_ids.append((m.id, r.id))

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        for maquina in maquinas:
            rid = None
            if execucao is not None:
                for mid, rid_val in resultados_ids:
                    if mid == maquina.id:
                        rid = rid_val
                        break
            future = executor.submit(worker, maquina, comando, arp_table, resultado_id=rid, os_alvo=os_alvo)
            futures.append(future)

        try:
            for future in as_completed(futures, timeout=timeout):
                try:
                    resultado = future.result()
                    resultados.append(resultado)
                except Exception as e:
                    logger.exception("Erro em worker paralelo: %s", e)
                    resultados.append({
                        "maquina": "desconhecida",
                        "ip": "N/A",
                        "os": "N/A",
                        "status": "erro",
                        "output": f"Erro interno no worker: {e}"
                    })

                if execucao is not None:
                    from execucoes.models import Execucao as ExecModel
                    from django.db.models import F
                    ExecModel.objects.filter(id=execucao.id).update(
                        concluidas=F('concluidas') + 1
                    )
        except TimeoutError:
            logger.error("Timeout global de %ss atingido na execução", timeout)
            for f in futures:
                f.cancel()
            if execucao is not None:
                from execucoes.models import Execucao as ExecModel
                ExecModel.objects.filter(id=execucao.id).update(status='falha')
            raise

    return resultados
