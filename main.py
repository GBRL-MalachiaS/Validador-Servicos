import psutil
import base64
import requests
import json
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

def listar_servicos():
    """
    Retorna um dicionário com todos os serviços ativos/inativos do servidor.
    """
    servicos_windows = {}
    for servico in psutil.win_service_iter():
        try:
            info = servico.as_dict()
            pid = servico.pid()
            if pid:
                processo = psutil.Process(pid)
                timestamp = processo.create_time()
                hora_inicio = datetime.fromtimestamp(timestamp)
                servicos_windows[info['name']] = {
                    'display_name': info.get('display_name', ''),
                    'status': info.get('status', ''),
                    'start_type': info.get('start_type', ''),
                    'date_time_start':hora_inicio.strftime("%d/%m/%Y - %H:%M:%S")
                    }
        except Exception as e:
            print(f"Erro ao acessar serviço: {e}")
            continue

        # Gera um arquivo json, com todos os status do serviços do windows
        with open('servicos.json', 'w', encoding='utf-8') as arquivo:
            json.dump(servicos_windows, arquivo, indent=4, ensure_ascii=False)

    return True

def validar_servico(nome_servico):
    """
    Valida se o serviço existe no sistema operacional.

    Args:
        nome_servico (str): Nome do serviço procurado.

    Returns:
        str: Mensagem informando que o serviço foi encontrado.

    Raises:
        ServiceNotFoundException: Se o serviço não for encontrado.
    """
    for servico in psutil.win_service_iter():
        if nome_servico.lower() in servico.name().lower():
            return f"Serviço {nome_servico} foi encontrado."
    raise ServiceNotFoundException(f"Serviço '{nome_servico}' não encontrado.")

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

def ultima_execucao(nome_servico):
    """
    Retorna a data e a hora da última execução do serviço.

    Args:
        nome_servico (str): Nome do serviço procurado.

    Returns:
        datetime: Data e hora da criação do processo.

    Raises:
        ServiceNotFoundException: Se o serviço não for encontrado.
        ServiceInactiveException: Se o serviço não possuir um processo ativo.
    """
    for servico in psutil.win_service_iter():
        if nome_servico.lower() in servico.name().lower():
            pid = servico.pid()
            if pid:
                processo = psutil.Process(pid)
                timestamp = processo.create_time()
                hora_inicio = datetime.fromtimestamp(timestamp)
                return hora_inicio
            else:
                raise ServiceInactiveException(
                    f"O serviço '{nome_servico}' está registrado, mas não possui um processo ativo.")
    raise ServiceNotFoundException(
        f"O serviço '{nome_servico}' não foi encontrado.")

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

# Função responsavel por gerar e carregar o arquivo Servicos.json
def carregar_servicos():
    # Chama a função listar serviços para gerar o arquivo serviços.json
    listar_servicos()
    with open('servicos.json', 'r', encoding='utf-8') as arquivo:
        return json.load(arquivo)


# --- EXEMPLO DE USO COM UM SERVIÇO PROPRIO VALIDANDO O LOG ---
if __name__ == "__main__":
    
    caminho_log = "../Frases_Servicos/dist/arquivos/log.xml"
    #caminho_log = "../Frases_Servicos/dist/arquivos/log_desatualizado.xml"
    nome_servico = "GBL-MeuServicoPython"
    resultado = validar_log_servico(caminho_log, nome_servico)

    if resultado:
        print("\nValidação do serviço:")
        print(f"Serviço: {resultado['servico']}")
        print(f"Status: {resultado['status']}")
        print(f"Última execução: {resultado['ultima_execucao']}")
        print(f"Log atualizado? {'Sim' if resultado['log_atualizado'] else 'Não'}")
