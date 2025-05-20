    # Validador de Serviços

    Este projeto tem como objetivo monitorar serviços do Windows, validar APIs e enviar alertas por e-mail caso algum serviço apresente problemas.

    ## Funcionalidades

    - **Listar Serviços**: Retorna um dicionário com todos os serviços ativos/inativos do servidor.
    - **Validar Serviço**: Verifica se um serviço específico existe no sistema operacional.
    - **Processamento do Serviço**: Retorna informações de uso de CPU, memória e status de um serviço.
    - **Última Execução**: Informa a data e hora da última execução de um serviço.
    - **Validar API**: Verifica se uma API está online e respondendo corretamente.
    - **Enviar E-mail**: Envia um e-mail de alerta caso um serviço apresente problemas.

    ## Requisitos

    - Python 3.x
    - [psutil](https://pypi.org/project/psutil/)
    - [requests](https://pypi.org/project/requests/)
    - [google-api-python-client](https://pypi.org/project/google-api-python-client/)
    - [google-auth](https://pypi.org/project/google-auth/)
    - [google-auth-oauthlib](https://pypi.org/project/google-auth-oauthlib/)

    ## Instalação

    1. Clone o repositório ou baixe os arquivos.

    2. Instale as dependências necessárias:
        ```
        pip install psutil requests google-api-python-client google-auth google-auth-oauthlib
        ```

    3. Configure as credenciais do Gmail:
        - Siga as instruções da [documentação oficial do Google](https://developers.google.com/gmail/api/quickstart/python) para obter o arquivo `token.json` e `credentials.json`.

    ## Como Usar

    1. Edite o arquivo `main.py` para definir o nome do serviço que deseja monitorar e a URL da API a ser validada.
    2. Execute o script:
        ```
        python main.py
        ```

    ## Observações

    - O script foi desenvolvido para sistemas Windows.
    - Certifique-se de executar o script com permissões administrativas para acessar informações dos serviços do sistema.
    - O envio de e-mails requer configuração prévia das credenciais do Gmail.

    ## Licença

    Este projeto está licenciado sob os termos da licença MIT.
    
    ## Contribuição

    Contribuições são bem-vindas! Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias, correções de bugs ou novas funcionalidades.

    1. Faça um fork do projeto.
    2. Crie uma branch para sua feature (`git checkout -b minha-feature`).
    3. Commit suas alterações (`git commit -am 'Adiciona nova feature'`).
    4. Faça push para a branch (`git push origin minha-feature`).
    5. Abra um Pull Request.

    ## Suporte

    Se você encontrar algum problema ou tiver dúvidas, abra uma issue neste repositório ou entre em contato pelo e-mail informado no código.

    ## Autor

    Gabriel Malachias  
    [LinkedIn](https://www.linkedin.com/in/gabriel-malachias/)  
    E-mail: gabriel.malachias@rte.com.br

    ---

    Este projeto não é afiliado, endossado ou suportado pela Google ou Microsoft. Use por sua conta e risco.
