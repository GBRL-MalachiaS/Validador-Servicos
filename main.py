import psutil
import base64
import requests
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from datetime import datetime, timedelta


def listar_servicos():
    servicos_windows = {}
    for servico in psutil.win_service_iter():
        try:
            info = servico.as_dict()
            servicos_windows[info['name']] = {
                'display_name': info.get('display_name', ''),
                'status': info.get('status', ''),
                'start_type': info.get('start_type', '')
            }
        except Exception as e:
            print(f"Erro ao acessar serviço: {e}")
            continue
    return servicos_windows


def validar_servico(nome_servico):
    for servico in psutil.win_service_iter():
        
        if nome_servico in servico.name():
            return f'Serviço de {nome_do_servico} foi encontrado.'
        
    return f"Serviço '{nome_servico}' não encontrado."


def processamento(nome_servico):
    for servico in psutil.win_service_iter():
        
        if nome_servico == servico.name():
            pid = servico.pid()
            processo = psutil.Process(pid)
            return {
                "nome": processo.name(),  # Metodo retorna o nome do processo
                # Metodo retornar o processamento de CPU
                "uso_cpu": processo.cpu_percent(interval=1),
                # Retorna o uso de memoria em MB
                "uso_memoria": processo.memory_info().rss / (1024 ** 2),
                # Valida se o serviço está rodando.
                "status": processo.status(),
            }


def ultima_execucao(nome_servico):
    for servico in psutil.win_service_iter():
        if nome_servico.lower() in servico.name().lower():
            pid = servico.pid()
            if pid:
                processo = psutil.Process(pid)
                timestamp = processo.create_time()
                hora_inicio = datetime.fromtimestamp(timestamp)
                return hora_inicio  # Retorna a dia e hora que foi a ultima execução do serviço
            else:
                return f"O serviço '{nome_servico}' está registrado, mas não possui um processo ativo."
    return f"O serviço '{nome_servico}' não foi encontrado."

def validar_api(url):
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


def enviar_email_api(mensagem,servico):
    creds = Credentials.from_authorized_user_file("token.json")

    # Cria a mensagem MIME
    msg = MIMEText(mensagem)
    msg["to"] = "gabriel.malachias@rte.com.br"
    msg["from"] = "gbl.malachias@gmail.com"
    msg["subject"] = f"Serviço {servico} - PROBLEMA"

    # Codifica a mensagem em base64
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        service = build("gmail", "v1", credentials=creds)
        message = {"raw": raw}
        send_message = service.users().messages().send(userId="me", body=message).execute()
        print(f"E-mail enviado! ID da mensagem: {send_message['id']}")
        return True
    except Exception as e:
        print(f"Erro ao enviar e-mail via API: {e}")
        return False



# Exemplo de uso
validar_api("https://api.adviceslip.com/advice")


nome_do_servico = 'LansweeperAgentService'
servicos = listar_servicos()
hora_atual = datetime.now()

print(processamento(nome_do_servico))

execucao = ultima_execucao(nome_do_servico)

if (hora_atual - execucao) > timedelta(minutes=60):
    enviar_email_api(f'O serviço {nome_do_servico}, foi executado a {execucao.strftime("%d/%m/%Y - %H:%M:%S")} a traz. \n necessário a ação humana',nome_do_servico)
