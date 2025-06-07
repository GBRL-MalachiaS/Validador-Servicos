"""Funções sem utilização! 
    """

# --- EXEMPLO DE USO COM MULTIPLOS SERVIÇOS ---
if __name__ == "__main__":
    # Validação da API - Conselhos Aleatórios
    validar_api("https://api.adviceslip.com/advice")

    while True:

        hora_atual = datetime.now()
        print("\nInicio da verificação:",
              hora_atual.strftime("%d/%m/%Y - %H:%M:%S"))
        # Carrega os serviços do JSON e lista como um dicionario
        servicos = carregar_servicos()

        # Itera sobre cada serviço presente no dicionario de serviços
        for nome_do_servico, info in servicos.items():
            print(f"\nValidando serviço: {nome_do_servico}")

            if info.get("status", "").lower() in ["running", "active"]:
                try:
                    print(validar_servico(nome_do_servico))

                    # Obtém dados de processamento e imprime
                    dados_processamento = processamento(nome_do_servico)
                    print("Dados de processamento:", dados_processamento)

                    # Obtém a última execução do serviço
                    execucao = ultima_execucao(nome_do_servico)
                    print("Horário da última execução:",
                          execucao.strftime("%d/%m/%Y - %H:%M:%S"))

                    # Verifica se a última execução ocorreu há mais de 60 minutos
                    if (hora_atual - execucao) > timedelta(minutes=60):
                        raise ServiceStaleExecutionException(
                            f'O serviço {nome_do_servico} foi executado em {execucao.strftime("%d/%m/%Y - %H:%M:%S")}, há mais de 60 minutos. A ação humana é necessária.'
                        )
                    else:
                        print("O serviço está sendo executado conforme esperado.")

                # Caso alguma exceção ocorra, dispara o alerta
                except (ServiceNotFoundException, ServiceInactiveException, ServiceStaleExecutionException) as e:
                    print(
                        f"Erro detectado no serviço '{nome_do_servico}': {e}")
                    enviar_email_api(str(e), nome_do_servico)
            else:
                print(
                    f"Serviço '{nome_do_servico}' não está ativo (Status: {info.get('status')}).")

        print('pause para o tempo de 5 minutos')
        # Tempo de espera para a proxima execução da função principal
        time.sleep(300)

# --- EXEMPLO DE USO COM UM SERVIÇO ---
if __name__ == "__main__":
    # Variavel para validação de um unico serviço
    nome_do_servico = 'LansweeperAgentService'

    # Validação da API - Conselhos Aleatórios
    validar_api("https://api.adviceslip.com/advice")

    while True:
        hora_atual = datetime.now()
        print("\nInicio da verificação:",
              hora_atual.strftime("%d/%m/%Y - %H:%M:%S"))

        try:
            # Valida se o serviço existe
            print(validar_servico(nome_do_servico))

            # Obtém e imprime dados de processamento
            dados_processamento = processamento(nome_do_servico)
            print("Dados de processamento:", dados_processamento)

            # Obtém a última execução do serviço
            execucao = ultima_execucao(nome_do_servico)
            print("Horário da última execução:",
                  execucao.strftime("%d/%m/%Y - %H:%M:%S"))

            # Se a última execução for anterior a 60 minutos, levanta exceção para disparar o alerta
            if (hora_atual - execucao) > timedelta(minutes=60):
                raise ServiceStaleExecutionException(
                    f'O serviço {nome_do_servico} foi executado em {execucao.strftime("%d/%m/%Y - %H:%M:%S")}, há mais de 60 minutos. A ação humana é necessária.'
                )
            else:
                print("O serviço está sendo executado conforme esperado.")

        # Caso ocorra qualquer uma das exceções relacionadas ao serviço, envia o e-mail de alerta
        except (ServiceNotFoundException, ServiceInactiveException, ServiceStaleExecutionException) as e:
            print(f"Erro detectado: {e}")
            enviar_email_api(str(e), nome_do_servico)

        # Tempo de espera para a proxima execução da função principal
        time.sleep(300)
