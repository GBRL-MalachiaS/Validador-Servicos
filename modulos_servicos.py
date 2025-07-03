import psutil
import base64
import requests
import socket
import os
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
import logging

# Configuração básica de logging para o main.py
# Isso ajudará a depurar problemas quando o script for executado diretamente ou via serviço
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

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


def processamento(nome_servico: str):
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
    logging.info(f"Procurando pelo serviço: {nome_servico}")
    for servico in psutil.win_service_iter():
        if nome_servico.lower() == servico.name().lower():
            try:
                pid = servico.pid()
                if pid is None:
                    raise ServiceInactiveException(
                        f"Serviço '{nome_servico}' não tem um PID ativo, pode estar parado ou em transição."
                    )
                processo = psutil.Process(pid)
                return {
                    "nome": processo.name(),
                    "uso_cpu": processo.cpu_percent(interval=1),
                    "uso_memoria": processo.memory_info().rss / (1024 ** 2),  # Memória em MB
                    "status": processo.status(),
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied, Exception) as e:
                raise ServiceInactiveException(
                    f"Erro ao processar o serviço {nome_servico} (PID: {servico.pid()}): {e}"
                )
    raise ServiceNotFoundException(
        f"Serviço '{nome_servico}' não foi encontrado para processamento."
    )


def validar_api(url: str):
    """
    Valida se a API enviada está em funcionamento.

    Args:
        url (str): URL da API a ser validada.

    Returns:
        bool: True se a API responder com status 200, False caso contrário.
    """
    try:
        logging.info(f"Validando API: {url}")
        # Aumentado o timeout para 10 segundos
        resposta = requests.get(url, timeout=10)
        if resposta.status_code == 200:
            logging.info("API está online e respondendo corretamente.")
            return True
        else:
            logging.warning(
                f"API respondeu com status: {resposta.status_code} para {url}")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro ao acessar a API {url}: {e}")
        return False


def enviar_email_api(mensagem: str, assunto: str, destinatario: str = "gabriel.malachias@rte.com.br", remetente: str = "gbl.malachias@gmail.com"):
    """
    Envia a mensagem de erro via e-mail usando a API do Gmail.

    Args:
        mensagem (str): Mensagem de erro a ser enviada.
        assunto (str): Assunto do e-mail.
        destinatario (str): Endereço de e-mail do destinatário.
        remetente (str): Endereço de e-mail do remetente.

    Returns:
        bool: True se o e-mail foi enviado com sucesso, False caso contrário.
    """
    try:
        # Carrega as credenciais do token.json.
        # Certifique-se de que este arquivo existe e está no mesmo diretório do script,
        # ou forneça o caminho completo.
        creds = Credentials.from_authorized_user_file("token.json")
    except Exception as e:
        logging.error(f"Erro ao carregar credenciais do token.json: {e}")
        logging.error(
            "Certifique-se de ter autenticado e gerado o arquivo 'token.json' seguindo as instruções da API do Google Gmail.")
        return False

    msg = MIMEText(mensagem)
    msg["to"] = destinatario
    msg["from"] = remetente
    msg["subject"] = assunto

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        service = build("gmail", "v1", credentials=creds)
        message = {"raw": raw}
        send_message = service.users().messages().send(
            userId="me", body=message).execute()
        logging.info(f"E-mail enviado! ID da mensagem: {send_message['id']}")
        return True
    except Exception as e:
        logging.error(f"Erro ao enviar e-mail via API: {e}")
        return False


def validar_log_servico(caminho_log: str, nome_servico: str):
    """
    Valida o log XML de um serviço, verificando a última execução e seu status.
    Em caso de problema (serviço parado ou log desatualizado), gera um alerta.

    Args:
        caminho_log (str): Caminho do arquivo XML de log.
        nome_servico (str): Nome do serviço a ser verificado.

    Returns:
        dict: Status do serviço, se está atualizado e última execução.
    """
    logging.info(
        f"Validando log do serviço '{nome_servico}' no caminho: {caminho_log}")
    status_servico = "Desconhecido"
    log_atualizado = False
    ultima_execucao_str = "N/A"

    try:
        # Lendo o arquivo XML
        if not os.path.exists(caminho_log):
            raise FileNotFoundError(
                f"Arquivo de log não encontrado: {caminho_log}")

        tree = ET.parse(caminho_log)
        root = tree.getroot()

        # Obtendo a última DataHora registrada
        datahora_element = root.find("Log/DataHora")
        if datahora_element is not None and datahora_element.text:
            ultima_execucao = datetime.strptime(
                datahora_element.text, "%Y-%m-%d %H:%M:%S")
            ultima_execucao_str = ultima_execucao.strftime("%d/%m/%Y %H:%M:%S")

            # Pegando a hora atual
            hora_atual = datetime.now()

            # Validando se o log está atualizado (menos de 60 minutos)
            log_atualizado = (
                hora_atual - ultima_execucao) <= timedelta(minutes=60)
        else:
            logging.warning(
                f"Elemento 'Log/DataHora' não encontrado ou vazio no log: {caminho_log}")
            log_atualizado = False  # Se não encontrar a data, considera desatualizado

        # Verificando status do serviço no Windows
        found_service_in_os = False
        for servico_os in psutil.win_service_iter():
            if nome_servico.lower() == servico_os.name().lower():
                status_servico = servico_os.status()
                found_service_in_os = True
                break

        if not found_service_in_os:
            status_servico = "Não Encontrado no OS"
            logging.warning(
                f"Serviço '{nome_servico}' não foi encontrado no sistema operacional.")

        # Se o serviço estiver parado ou o log estiver desatualizado, gera alerta
        if status_servico.lower() != "running" or not log_atualizado:
            mensagem_alerta = f"Alerta! Serviço '{nome_servico}' em problema!\n\n" \
                f"Status atual: {status_servico}\n" \
                f"Última execução registrada: {ultima_execucao_str}\n" \
                f"Log atualizado (últimos 60 min)? {'Sim' if log_atualizado else 'Não'}"
            assunto_email = f"ALERTA: Serviço {nome_servico} - PROBLEMA"
            enviar_email_api(mensagem_alerta, assunto_email)
            logging.warning(f"Alerta gerado para o serviço '{nome_servico}'.")

        return {
            "servico": nome_servico,
            "status": status_servico,
            "log_atualizado": log_atualizado,
            "ultima_execucao": ultima_execucao_str
        }

    except FileNotFoundError as e:
        logging.error(
            f"Erro: {e}. Verifique o caminho do arquivo de log para '{nome_servico}'.")
        mensagem_erro = f"Alerta! Problema com o log do serviço '{nome_servico}'!\n\n" \
            f"Erro: Arquivo de log não encontrado em '{caminho_log}'.\n" \
            f"Verifique se o serviço está gerando o log corretamente ou se o caminho está certo."
        assunto_email = f"ALERTA: Serviço {nome_servico} - ERRO DE LOG"
        enviar_email_api(mensagem_erro, assunto_email)
        return {
            "servico": nome_servico,
            "status": "Erro de Log",
            "log_atualizado": False,
            "ultima_execucao": "N/A"
        }
    except ET.ParseError as e:
        logging.error(
            f"Erro ao parsear XML do log para '{nome_servico}': {e}. Caminho: {caminho_log}")
        mensagem_erro = f"Alerta! Problema com o log XML do serviço '{nome_servico}'!\n\n" \
            f"Erro ao ler o arquivo XML em '{caminho_log}': {e}.\n" \
            f"Verifique a integridade do arquivo de log."
        assunto_email = f"ALERTA: Serviço {nome_servico} - ERRO NO XML DO LOG"
        enviar_email_api(mensagem_erro, assunto_email)
        return {
            "servico": nome_servico,
            "status": "Erro de XML",
            "log_atualizado": False,
            "ultima_execucao": "N/A"
        }
    except Exception as e:
        logging.error(
            f"Erro inesperado ao validar o log do serviço '{nome_servico}': {e}")
        mensagem_erro = f"Alerta! Erro inesperado ao validar o serviço '{nome_servico}'!\n\n" \
            f"Detalhes do erro: {e}.\n" \
            f"Caminho do log: {caminho_log}"
        assunto_email = f"ALERTA: Serviço {nome_servico} - ERRO INESPERADO"
        enviar_email_api(mensagem_erro, assunto_email)
        return {
            "servico": nome_servico,
            "status": "Erro",
            "log_atualizado": False,
            "ultima_execucao": "N/A"
        }


def validar_pasta(caminho_pasta: str, nome_pasta: str, nome_servidor: str):
    """
    Valida se um caminho de pasta existe e envia um e-mail se não existir.
    """
    logging.info(
        f"Validando pasta '{nome_pasta}' em '{caminho_pasta}' no servidor '{nome_servidor}'...")
    if not os.path.exists(caminho_pasta):
        logging.warning(
            f"A pasta '{caminho_pasta}' NÃO FOI ENCONTRADA no servidor '{nome_servidor}'."
        )
        mensagem_erro = (f"Alerta de infraestrutura!\n\n"
                         f"A pasta '{nome_pasta}' com o caminho esperado '{caminho_pasta}' "
                         f"não foi encontrada no servidor '{nome_servidor}'.\n\n"
                         f"Por favor, verifique a integridade do ambiente.")
        assunto_email = f"ALERTA: {nome_servidor} - PASTA '{nome_pasta}' NÃO ENCONTRADA"
        enviar_email_api(mensagem_erro, assunto_email)
    else:
        logging.info(f"Pasta '{nome_pasta}' encontrada em '{caminho_pasta}'.")


def analisar_infraestrutura_local(config: dict):
    """
    Identifica o servidor local e executa apenas as validações configuradas para ele.

    Args:
        config (dict): Dicionário de configuração contendo os detalhes dos servidores.
    """
    logging.info("--- INICIANDO ROTINA DE MONITORIZAÇÃO ---")

    # Obtém o hostname da máquina local e converte para maiúsculas
    hostname_local = socket.gethostname().upper()
    logging.info(f"Executando no servidor: {hostname_local}")

    # Verifica se o servidor local está no dicionário de configuração
    if hostname_local in config:
        logging.info(
            f"Configuração encontrada para '{hostname_local}'. Iniciando validações..."
        )
        detalhes_servidor_atual = config[hostname_local]

        # Validação dos Serviços (baseado no log)
        if "Servicos" in detalhes_servidor_atual and detalhes_servidor_atual["Servicos"]:
            logging.info("\n[+] Validando Serviços...")
            for nome_servico, caminho_log in detalhes_servidor_atual["Servicos"].items():
                logging.info(f"  > Validando serviço: {nome_servico}...")
                resultado = validar_log_servico(caminho_log, nome_servico)
                if resultado:
                    status = resultado['status']
                    log_ok = resultado['log_atualizado']
                    if status.lower() == "running" and log_ok:
                        logging.info(
                            f"  [OK] Serviço '{nome_servico}' está ativo e com log atualizado. Status: {status}, Última Execução: {resultado['ultima_execucao']}"
                        )
                    else:
                        logging.warning(
                            f"  [ALERTA] Problema encontrado no serviço '{nome_servico}'. Status: {status}, Log Atualizado: {log_ok}. Última Execução: {resultado['ultima_execucao']}"
                        )
                else:
                    logging.error(
                        f"  [ERRO] Falha ao processar a validação do serviço '{nome_servico}'. Verifique o log do monitor."
                    )

        # Validação das Pastas
        if "pastas" in detalhes_servidor_atual and detalhes_servidor_atual["pastas"]:
            logging.info("\n[+] Validando Pastas...")
            for nome_pasta, caminho in detalhes_servidor_atual["pastas"].items():
                validar_pasta(caminho, nome_pasta, hostname_local)

        # 3. Validação das APIs (se houver no config)
        if "APIs" in detalhes_servidor_atual and detalhes_servidor_atual["APIs"]:
            logging.info("\n[+] Validando APIs...")
            for nome_api, url_api in detalhes_servidor_atual["APIs"].items():
                logging.info(f"  > Validando API: {nome_api} ({url_api})...")
                if validar_api(url_api):
                    logging.info(f"  [OK] API '{nome_api}' está online.")
                else:
                    logging.warning(
                        f"  [ALERTA] API '{nome_api}' em '{url_api}' está offline ou com problemas.")
                    mensagem_alerta = (f"Alerta de infraestrutura!\n\n"
                                       f"A API '{nome_api}' no endereço '{url_api}' "
                                       f"não está respondendo ou retornou um status inesperado no servidor '{hostname_local}'.\n\n"
                                       f"Por favor, verifique a disponibilidade da API.")
                    assunto_email = f"ALERTA: {hostname_local} - API '{nome_api}' COM PROBLEMA"
                    enviar_email_api(mensagem_alerta, assunto_email)

        logging.info(
            f"\n--- Validações para '{hostname_local}' finalizadas. ---")

    else:
        logging.warning(
            f"\n[AVISO] O servidor '{hostname_local}' não foi encontrado no dicionário de configuração."
        )
        logging.warning(
            "Nenhuma ação de monitorização será executada nesta máquina.")

    logging.info("\n--- ROTINA DE MONITORIZAÇÃO FINALIZADA ---")


def carregar_configuracao(caminho_arquivo: str = 'config.json') -> dict:
    """
    Carrega o arquivo de configuração JSON.

    Args:
        caminho_arquivo (str): Caminho para o arquivo de configuração.

    Returns:
        dict: O conteúdo do arquivo JSON como um dicionário, ou um dicionário vazio em caso de erro.
    """
    try:
        with open(caminho_arquivo, 'r', encoding='utf-8') as file:
            config = json.load(file)
            logging.info(
                f"Arquivo de configuração '{caminho_arquivo}' carregado com sucesso.")
            return config
    except FileNotFoundError:
        logging.error(
            f"Erro: Arquivo de configuração não encontrado em '{caminho_arquivo}'.")
        return {}
    except json.JSONDecodeError as e:
        logging.error(
            f"Erro de sintaxe no arquivo de configuração '{caminho_arquivo}': {e}.")
        return {}
    except Exception as e:
        logging.error(
            f"Erro inesperado ao carregar a configuração de '{caminho_arquivo}': {e}.")
        return {}


if __name__ == "__main__":
    # Arquivo de configuração, para serviços.
    arquivo_config = './config.json'
    configuracao = carregar_configuracao(arquivo_config)

    if configuracao:
        analisar_infraestrutura_local(configuracao)
    else:
        logging.error(
            "Configuração não pôde ser carregada. A rotina de monitoramento não será executada.")
