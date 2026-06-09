import ipaddress
import platform
import socket
import threading
import subprocess
import os
import time
from decouple import config

NCC_PASSWORD = config('NCC_ADMIN_PASSWORD', default='senha_padrao')


def _ping_responde(ip):
    sistema = platform.system().lower()

    if sistema == "windows":
        comando = ["ping", "-n", "1", "-w", "1000", ip]
    else:
        comando = ["ping", "-c", "1", "-W", "1", ip]

    resultado = subprocess.run(comando, capture_output=True, text=True)
    return resultado.returncode == 0


def _broadcast_para_ip(ip):
    try:
        rede = ipaddress.ip_network(f"{ip}/24", strict=False)
        return str(rede.broadcast_address)
    except ValueError:
        return "255.255.255.255"


def enviar_wol(mac, ip=None, porta=9):
    mac_limpo = mac.replace("-", ":").replace(".", "").lower().replace(":", "")
    pacote = bytes.fromhex("ff" * 6 + mac_limpo * 16)
    destino = _broadcast_para_ip(ip) if ip else "255.255.255.255"

    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(pacote, (destino, porta))


def garantir_maquina_ligada(ip, mac, tentativas=12, intervalo=5):
    """Tenta ping; se não responder envia WOL e espera.

    Retorna tupla (online: bool, mensagem: str|None, wol_enviado: bool).
    """
    # Se já responde ao ping, não enviamos WOL
    if _ping_responde(ip):
        return True, None, False

    # Não respondeu: envia WOL e aguarda
    enviar_wol(mac, ip)

    for _ in range(tentativas):
        time.sleep(intervalo)
        if _ping_responde(ip):
            return True, None, True

    return False, f"Máquina não respondeu ao ping após Wake on LAN em {tentativas * intervalo}s.", True

def executar_linux(ip, comando):
    """
    Usa sshpass para passar a senha automaticamente e evita travar o Python.
    StrictHostKeyChecking=no evita o erro de 'conhece este host?'.
    """
    cmd = (
        f"sshpass -p '{NCC_PASSWORD}' "
        f"ssh -o ConnectTimeout=3 -o StrictHostKeyChecking=no "
        f"ncc@{ip} '{comando}'"
    )
    # Usamos check_output ou getoutput para capturar o resultado
    return subprocess.getoutput(cmd)

def executar_windows(ip, comando):
    cmd = [
        "sshpass", "-p", NCC_PASSWORD,
        "ssh",
        "-o", "ConnectTimeout=3",
        "-o", "StrictHostKeyChecking=no",
        "-o", "PreferredAuthentications=password",
        "-o", "PubkeyAuthentication=no",
        f"ncc@{ip}",
        comando
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding='cp1252', errors='replace')  
    
    if result.returncode == 0:
        return result.stdout
    else:
        return result.stderr

def detectar_os(ip):
    # Também precisa de sshpass para não travar na detecção
    cmd = (
        f"sshpass -p '{NCC_PASSWORD}' "
        f"ssh -o ConnectTimeout=2 -o StrictHostKeyChecking=no "
        f"ncc@{ip} exit"
    )
    teste = os.system(cmd)
    return "debian" if teste == 0 else "windows"

def worker(maquina, comando, arp_table, resultados, lock):
    # Normaliza o MAC que veio do banco para garantir a comparação
    mac_banco = maquina.mac_address.lower().replace('-', ':')
    
    # 1. Tenta pegar IP atual via ARP
    ip = arp_table.get(mac_banco)
    
    # 2. Fallback: Se não está no ARP, usa o último IP conhecido
    if not ip:
        ip = maquina.ultimo_ip
        usa_fallback = True
    else:
        usa_fallback = False

    if not ip:
        with lock:
            resultados.append({
                "maquina": maquina.nome,
                "status": "offline",
                "ip": "Nenhum", 
                "os": "N/A",    
                "output": "Máquina não localizada na rede (ARP/DB)."
            })
        return

    online, mensagem, wol_enviado = garantir_maquina_ligada(ip, mac_banco)
    if not online:
        with lock:
            resultados.append({
                "maquina": maquina.nome,
                "ip": ip,
                "os": "N/A",
                "status": "offline",
                "output": mensagem,
            })
        return

    # 3. Lógica de detecção de OS (se dual boot)
    os_execucao = maquina.tipo_os
    if maquina.tipo_os == "dual":
        # Se tiver sido necessário enviar WOL (estava desligado), preferir executar no Linux
        if wol_enviado:
            os_execucao = "debian"
        else:
            os_execucao = detectar_os(ip)

    try:
        if os_execucao == "debian":
            output = executar_linux(ip, comando.comando_linux)
        else:
            output = executar_windows(ip, comando.comando_windows)
        
        status = "sucesso"
        
        # 4. SUCESSO! Vamos salvar esse IP para não depender só do ARP na próxima
        if ip != maquina.ultimo_ip:
            maquina.ultimo_ip = ip
            maquina.save() # Django salva no BD

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