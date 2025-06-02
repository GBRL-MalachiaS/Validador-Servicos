import requests
import os
import csv
import time
import xml.etree.ElementTree as ET
import datetime


# URL da API
url = "https://api.adviceslip.com/advice"

comunicacao = requests.get(url)

frase = comunicacao.json()

# Caminho do arquivo CSV
caminho_arquivo_csv = "./servico_teste/dados.csv"

# Criando o diretório se não existir
os.makedirs(os.path.dirname(caminho_arquivo_csv), exist_ok=True)

# Obtendo o dicionário de dados
dicionario_frase = frase["slip"]

arquivo_existe = os.path.exists(caminho_arquivo_csv)

if __name__ == "__main__":
    
    while True:

        with open(caminho_arquivo_csv, mode="a", newline="", encoding="utf-8") as dados:
            escritor = csv.writer(dados, delimiter=";")

            # Se o arquivo não existe, adiciona a linha de cabeçalho
            if not arquivo_existe:
                escritor.writerow(dicionario_frase.keys())  # Escreve os nomes das colunas

            # Adiciona os valores da API como uma nova linha
            escritor.writerow(dicionario_frase.values())
            print('Feita a Gravação')

        # Criando a estrutura XML
        criar_xml = ET.Element("Logs")
        entrada_log = ET.SubElement(criar_xml, "Log")

        # Capturando data e hora
        data_hora_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ET.SubElement(entrada_log, "DataHora").text = data_hora_atual
        ET.SubElement(entrada_log, "Mensagem").text = "Execução bem-sucedida"

        # Convertendo a estrutura para string XML
        tree = ET.ElementTree(criar_xml)

        # Salvando em um arquivo
        with open("./servico_teste/log.xml", "wb") as arquivo:
            tree.write(arquivo, encoding="utf-8", xml_declaration=True)
            print('Log Gerado')

        time.sleep(30)