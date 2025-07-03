import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import socket
import time
import os
import logging  # Importar a biblioteca de logging

# importe suas funções
# Certifique-se de que main.py está no mesmo diretório ou no PYTHONPATH
from modulos_servicos import carregar_configuracao, analisar_infraestrutura_local

# Configurar o logging para o serviço
# O servicemanager é usado para logar eventos no Visualizador de Eventos do Windows
# Para logs mais detalhados para depuração, você pode configurar um FileHandler aqui
# Exemplo de configuração de logging para arquivo:
# logging.basicConfig(
#     filename='C:\\Logs\\MonitorInfraService.log', # Caminho para o arquivo de log
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s'
# )
# Para o serviço, é melhor usar servicemanager.LogMsg para eventos críticos
# e o logging padrão para detalhes internos da execução, que podem ser direcionados para um arquivo.


class MonitorInfraService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MonitorInfraService"
    _svc_display_name_ = "Monitoramento de Infraestrutura"
    _svc_description_ = "Serviço que monitora logs, serviços e pastas em servidores Windows."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.running = True
        self.config_path = './config.json'  # Caminho para o arquivo de configuração
        self.intervalo_execucao_segundos = 3600  # 1 hora
        self.intervalo_erro_segundos = 300  # 5 minutos em caso de erro

        # Configura o logger específico para o serviço para direcionar para o Visualizador de Eventos
        self.logger = logging.getLogger(self._svc_name_)
        self.logger.setLevel(logging.INFO)

        # Adiciona um handler para o Visualizador de Eventos
        # É importante notar que LogMsg é o método preferencial para eventos no SCM
        # Mas para logs internos mais detalhados, FileHandler é melhor.
        # Aqui, vamos nos focar em usar servicemanager.LogMsg para eventos visíveis no Windows.

    def SvcStop(self):
        """Chamado quando o serviço recebe um comando de parada."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        servicemanager.LogInfoMsg(
            f"{self._svc_name_} - Serviço recebendo comando de parada.")
        self.running = False
        win32event.SetEvent(self.hWaitStop)

    def SvcDoRun(self):
        """Chamado quando o serviço é iniciado."""
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ''))
        servicemanager.LogInfoMsg(
            f"{self._svc_name_} - Serviço iniciado com sucesso.")
        self.main()

    def main(self):
        """Loop principal de execução do serviço."""
        while self.running:
            try:
                servicemanager.LogInfoMsg(
                    f"{self._svc_name_} - Iniciando ciclo de monitoramento.")
                config = carregar_configuracao(self.config_path)
                if config:
                    analisar_infraestrutura_local(config)
                    servicemanager.LogInfoMsg(
                        f"{self._svc_name_} - Ciclo de monitoramento concluído. Próxima execução em {self.intervalo_execucao_segundos / 60} minutos.")
                    # Espera pelo próximo ciclo ou por um evento de parada
                    win32event.WaitForSingleObject(
                        self.hWaitStop, self.intervalo_execucao_segundos * 1000)
                else:
                    servicemanager.LogErrorMsg(
                        f"{self._svc_name_} - Falha ao carregar configuração. Tentando novamente em {self.intervalo_erro_segundos / 60} minutos.")
                    win32event.WaitForSingleObject(
                        self.hWaitStop, self.intervalo_erro_segundos * 1000)
            except Exception as e:
                # Loga o erro no Visualizador de Eventos do Windows
                servicemanager.LogErrorMsg(
                    f"{self._svc_name_} - Erro inesperado no loop principal: {str(e)}")
                # Em caso de erro, espera um tempo menor para tentar novamente
                servicemanager.LogInfoMsg(
                    f"{self._svc_name_} - Erro ocorrido, tentando novamente em {self.intervalo_erro_segundos / 60} minutos.")
                win32event.WaitForSingleObject(
                    self.hWaitStop, self.intervalo_erro_segundos * 1000)

        servicemanager.LogInfoMsg(f"{self._svc_name_} - Serviço finalizado.")


if __name__ == '__main__':
    # Este bloco é executado quando o script é chamado via linha de comando
    # para instalar, desinstalar, iniciar ou parar o serviço.
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MonitorInfraService)
        servicemanager.StopRunning()
    else:
        win32serviceutil.HandleCommandLine(MonitorInfraService)
