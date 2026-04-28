import cmd
import threading
import subprocess
import os
from decouple import config

NCC_PASSWORD = config('NCC_ADMIN_PASSWORD', default='senha_padrao')

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

    # 3. Lógica de detecção de OS (se dual boot)
    os_execucao = maquina.tipo_os
    if maquina.tipo_os == "dual":
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