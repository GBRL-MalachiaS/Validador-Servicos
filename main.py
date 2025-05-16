import psutil
import smtplib
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


nome_do_servico = "WinDefend"
hora_atual = datetime.now()
# print(validar_servico(nome_do_servico))
# print(processamento(nome_do_servico))
execucao = ultima_execucao(nome_do_servico)

tempo_sem_execucao = hora_atual - execucao

if tempo_sem_execucao > timedelta(minutes=60):
    creds = Credentials.from_authorized_user_file("token.json")

    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
    server.starttls()
    server.login(creds.token, creds.token_uri)  # Autenticando via OAuth
    server.sendmail("tecnologiarte607@gmail.com", "gabriel.malachias@rte.com.br", "Testando envio de e-mail via OAuth")
    server.quit()

    print('é maior')
