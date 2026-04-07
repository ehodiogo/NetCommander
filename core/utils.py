import subprocess
import re
import platform
import os

def atualizar_cache_rede(base_ip="10.1.4.35"):
    """
    Faz um ping rápido no broadcast ou em um range para popular o ARP.
    """
    sistema = platform.system().lower()
    # No Windows, o ping de broadcast nem sempre funciona, 
    # então um loop rápido em alguns IPs conhecidos ou no gateway ajuda.
    if sistema == "windows":
        for i in range(1, 10): # Testa os primeiros 10 IPs como exemplo
            os.system(f"ping -n 1 -w 100 {base_ip}.{i} > nul")
    else:
        # No Linux, o fping é excelente para isso (se instalado)
        os.system(f"ping -b -c 1 {base_ip}.255 > /dev/null 2>&1")

def scan_arp():
    """
    Retorna dict: {mac: ip}. Tenta popular o cache antes de ler.
    """
    # 1. Tentar popular o cache ARP (Ping de broadcast)
    # Substitua pelo seu range de rede (ex: 192.168.1.255)
    sistema = platform.system().lower()
    try:
        if sistema == "windows":
            # Se o servidor for Windows, varre o range da sua rede 10.1.4.x
            subprocess.run("for /L %i in (1,1,10) do @ping -n 1 -w 100 10.1.4.%i > nul", shell=True)
        else:
            # Se for Linux (como o seu iMac), pinga o broadcast correto da rede 10.1.4.x
            subprocess.run(["ping", "-b", "-c", "1", "10.1.4.255"], capture_output=True, timeout=2)
    except:
        pass

    try:
        output = subprocess.check_output("arp -a", shell=True).decode(...)
        print("--- DEBUG: SAÍDA BRUTA DO COMANDO ARP ---")
        print(output) # Isso vai imprimir o print do terminal no seu console do Django
        print("---------------------------------------")
    except:
        return {}

    # 2. Ler a tabela ARP
    try:
        output = subprocess.check_output("arp -a", shell=True).decode('cp1252' if sistema == "windows" else 'utf-8')
    except:
        return {}

    result = {}
    lines = output.splitlines()
    for line in lines:
        # Regex para capturar IP e MAC (aceita formatos com - e :)
        ip_match = re.search(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
        mac_match = re.search(r'([0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})', line)
        
        if ip_match and mac_match:
            # Normalização CRÍTICA: tudo minúsculo e usando ":"
            mac = mac_match.group(1).lower().replace('-', ':')
            ip = ip_match.group(1)
            print(f"--- MÁQUINA ENCONTRADA: MAC {mac} -> IP {ip} ---")
            result[mac] = ip
    return result