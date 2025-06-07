import psutil
import base64
import requests
import socket
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# Exceções customizadas para tratamento dos serviços
class ServiceNotFoundException(Exception):
    """Exceção disparada quando o serviço não é encontrado."""
    pass

class ServiceInactiveException(Exception):
    """Exceção disparada quando o serviço está registrado, mas não possui um processo ativo ou não pode ser processado."""
    pass

class ServiceStaleExecutionException(Exception):
    """Exceção disparada quando a última execução do serviço é anterior ao tempo permitido."""
    pass

# Configurações de servidores o que tem que validar em cada um 
dicionario_servicos = {
    "607-113995": {
        "Serviços": {
            "GBL-MeuServicoPython": "../Frases_Servicos/dist/arquivos/log.xml",
        },
        "pastas": {
            "Logs_Serviço_GBL": "../Frases_Servicos/dist/arquivos/",
        }
    }

}

def processamento(nome_servico):
    """
    Retorna os dados de processamento do serviço.

    Args:
        nome_servico (str): Nome do serviço procurado.

    Returns:
        dict: Dicionário com nome, uso de CPU, memória e status do processo.

    Raises:
        ServiceNotFoundException: Se o serviço não for encontrado.
        ServiceInactiveException: Se ocorrer erro ao acessar o processo do serviço.
    """
    for servico in psutil.win_service_iter():
        if nome_servico.lower() == servico.name().lower():
            try:
                pid = servico.pid()
                processo = psutil.Process(pid)
                return {
                    "nome": processo.name(),
                    "uso_cpu": processo.cpu_percent(interval=1),
                    "uso_memoria": processo.memory_info().rss / (1024 ** 2),
                    "status": processo.status(),
                }
            except Exception as e:
                raise ServiceInactiveException(
                    f"Erro ao processar o serviço {nome_servico}: {e}")
    raise ServiceNotFoundException(
        f"Serviço '{nome_servico}' não foi encontrado para processamento.")

def validar_api(url):
    """
    Valida se a API enviada está em funcionamento.

    Args:
        url (str): URL da API a ser validada.

    Returns:
        bool: True se a API responder com status 200, False caso contrário.
    """
    try:
        resposta = requests.get(url, timeout=5)
        if resposta.status_code == 200:
            print("API está online e respondendo corretamente.")
            return True
        else:
            print(f"API respondeu com status: {resposta.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Erro ao acessar a API: {e}")
        return False

def validar_log_servico(caminho_log, nome_servico):
    """
    Valida o log XML de um serviço, verificando a última execução e seu status.
    Caso o serviço esteja parado ou com log desatualizado, dispara um e-mail de alerta.

    Args:
        caminho_log (str): Caminho do arquivo XML de log.
        nome_servico (str): Nome do serviço a ser verificado.

    Returns:
        dict: Status do serviço e se está atualizado.
    """
    try:
        # Lendo o arquivo XML
        tree = ET.parse(caminho_log)
        root = tree.getroot()

        # Obtendo a última DataHora registrada
        ultima_datahora_str = root.find("Log/DataHora").text
        ultima_execucao = datetime.strptime(ultima_datahora_str, "%Y-%m-%d %H:%M:%S")

        # Pegando a hora atual
        hora_atual = datetime.now()

        # Validando se o log está atualizado (menos de 60 minutos)
        log_atualizado = (hora_atual - ultima_execucao) <= timedelta(minutes=60)

        # Verificando status do serviço no Windows
        status_servico = "Desconhecido"
        for servico in psutil.win_service_iter():
            if nome_servico.lower() == servico.name().lower():
                status_servico = servico.status()

        # Se o serviço estiver parado ou o log estiver desatualizado, envia alerta
        if status_servico.lower() != "running" or not log_atualizado:
            mensagem_erro = f"Serviço '{nome_servico}' está com problemas!\n\n" \
                            f"Status: {status_servico}\nÚltima execução registrada: {ultima_execucao.strftime('%d/%m/%Y %H:%M:%S')}\n" \
                            f"Log atualizado? {'Sim' if log_atualizado else 'Não'}"
            enviar_email_api(mensagem_erro, nome_servico)

        return {
            "servico": nome_servico,
            "status": status_servico,
            "log_atualizado": log_atualizado,
            "ultima_execucao": ultima_execucao.strftime("%d/%m/%Y %H:%M:%S")
        }

    except Exception as e:
        print(f"Erro ao validar o log do serviço: {e}")
        return None

def enviar_email_api(mensagem, servico):
    """
    Envia a mensagem de erro via e-mail caso o serviço apresente problema.

    Args:
        mensagem (str): Mensagem de erro a ser enviada.
        servico (str): Nome do serviço que apresentou problema.

    Returns:
        bool: True se o e-mail foi enviado com sucesso, False caso contrário.
    """
    creds = Credentials.from_authorized_user_file("token.json")
    msg = MIMEText(mensagem)
    msg["to"] = "gabriel.malachias@rte.com.br"
    msg["from"] = "gbl.malachias@gmail.com"
    msg["subject"] = f"Serviço {servico} - PROBLEMA"

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        service = build("gmail", "v1", credentials=creds)
        message = {"raw": raw}
        send_message = service.users().messages().send(
            userId="me", body=message).execute()
        print(f"E-mail enviado! ID da mensagem: {send_message['id']}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail via API: {e}")
        return False

def validar_caminho_pasta(caminho_pasta, nome_pasta, nome_servidor):
    """
    Valida se um caminho de pasta existe e envia um e-mail se não existir.
    """
    print(f"  > Validando pasta '{nome_pasta}' em '{caminho_pasta}'...")
    if not os.path.exists(caminho_pasta):
        print(f"  [ALERTA] A pasta '{caminho_pasta}' NÃO FOI ENCONTRADA no servidor '{nome_servidor}'.")
        mensagem_erro = (f"Alerta de infraestrutura!\n\n"
                         f"A pasta '{nome_pasta}' com o caminho esperado '{caminho_pasta}' "
                         f"não foi encontrada no servidor '{nome_servidor}'.\n\n"
                         f"Por favor, verifique a integridade do ambiente.")
        enviar_email_api(mensagem_erro, f"{nome_servidor} - PASTA NÃO ENCONTRADA")
    else:
        print(f"  [OK] Pasta '{nome_pasta}' encontrada.")

def analisar_infraestrutura_local(config): 
    """
    Identifica o servidor local e executa apenas as validações configuradas para ele.
    """
    print("--- INICIANDO ROTINA DE MONITORIZAÇÃO ---")
    
    # Obtém o hostname da máquina local e converte para maiúsculas
    hostname_local = socket.gethostname().upper()
    print(f"Executando no servidor: {hostname_local}")

    # Verifica se o servidor local está no dicionário de configuração
    if hostname_local in config:
        print(f"Configuração encontrada para '{hostname_local}'. Iniciando validações...")
        detalhes_servidor_atual = config[hostname_local]

        # Validação dos Serviços (baseado no log)
        if "Serviços" in detalhes_servidor_atual and detalhes_servidor_atual["Serviços"]:
            print("\n[+] Validando Serviços...")
            for nome_servico, caminho_log in detalhes_servidor_atual["Serviços"].items():
                print(f"  > Validando serviço: {nome_servico}...")
                resultado = validar_log_servico(caminho_log, nome_servico)
                if resultado:
                    status = resultado['status']
                    log_ok = resultado['log_atualizado']
                    if status.lower() == "running" and log_ok:
                        print(f"  [OK] Serviço '{nome_servico}' está ativo e com log atualizado.")
                    else:
                        print(f"  [ALERTA] Problema encontrado no serviço '{nome_servico}'. Status: {status}, Log Atualizado: {log_ok}.")
                else:
                    print(f"  [ERRO] Falha ao processar a validação do serviço '{nome_servico}'. Verifique o log do monitor.")

        # 2. Validação das Pastas
        if "pastas" in detalhes_servidor_atual and detalhes_servidor_atual["pastas"]:
            print("\n[+] Validando Pastas...")
            for nome_pasta, caminho in detalhes_servidor_atual["pastas"].items():
                validar_caminho_pasta(caminho, nome_pasta, hostname_local)
        
        print(f"\n--- Validações para '{hostname_local}' finalizadas. ---")

    else:
        # O que fazer se o servidor não estiver no dicionário
        print(f"\n[AVISO] O servidor '{hostname_local}' não foi encontrado no dicionário de configuração.")
        print("Nenhuma ação de monitorização será executada nesta máquina.")

    print("\n--- ROTINA DE MONITORIZAÇÃO FINALIZADA ---")

# --- EXEMPLO DE USO COM UM SERVIÇO PROPRIO VALIDANDO O LOG ---
if __name__ == "__main__":
      
    # caminho_log = "../Frases_Servicos/dist/arquivos/log.xml"
    # #caminho_log = "../Frases_Servicos/dist/arquivos/log_desatualizado.xml"
    # nome_servico = "GBL-MeuServicoPython"
    # resultado = validar_log_servico(caminho_log, nome_servico)

    # if resultado:
    #     print("\nValidação do serviço:")
    #     print(f"Serviço: {resultado['servico']}")
    #     print(f"Status: {resultado['status']}")
    #     print(f"Última execução: {resultado['ultima_execucao']}")
    #     print(f"Log atualizado? {'Sim' if resultado['log_atualizado'] else 'Não'}")
        
        analisar_infraestrutura_local(dicionario_servicos)
