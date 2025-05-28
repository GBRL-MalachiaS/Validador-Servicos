import main
import json


servicos = main.listar_servicos()

with open('servicos.json', 'w', encoding='utf-8') as arquivo:
    json.dump(servicos, arquivo, indent=4, ensure_ascii=False)

print("Arquivo gerado!")