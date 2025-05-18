import psutil
import smtplib
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime, timedelta


servicos_windows = {}


def validar_servico(nome_servico):
    for servico in psutil.win_service_iter():
        servicos_windows.update(
            {servico.pid(): {servico.name(): servico.display_name()}})
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


def enviar_email(mensagem):
    if mensagem is not None:
        # Carregar credenciais OAuth do arquivo JSON
        creds = Credentials.from_authorized_user_file("token.json")

        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())

        SMTP_SERVER = "smtp.gmail.com"
        SMTP_PORT = 587
        EMAIL_REMETENTE = "gbl.malachias@gmail.com"
        EMAIL_DESTINO = "gabriel.malachias@rte.com.br"

        # Criando mensagem formatada corretamente
        msg = MIMEText(mensagem)
        msg["Subject"] = "Teste de envio com OAuth2"
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = EMAIL_DESTINO

        try:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()

            # Autenticação via OAuth2
            auth_string = f"user={EMAIL_REMETENTE}\x01auth=Bearer {creds.token}\x01\x01"
            server.docmd("AUTH", "XOAUTH2 " + auth_string)

            # Envio do e-mail
            server.sendmail(EMAIL_REMETENTE, EMAIL_DESTINO, msg.as_string())
            server.quit()
            return True

        except Exception as e:
            print(f"Erro ao enviar e-mail: {e}")
            return False

    return False


nome_do_servico = "WinDefend"
hora_atual = datetime.now()
# print(validar_servico(nome_do_servico))
# print(processamento(nome_do_servico))
execucao = ultima_execucao(nome_do_servico)

# tempo_sem_execucao = hora_atual - execucao

# if tempo_sem_execucao > timedelta(minutes=60):
#     print('é maior')
# else:
print('Está dentro dos 60 mim')
msg = "aqui está o teste de envio."
enviar_email('texto de teste')
