from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

# Fluxo de autenticação OAuth2
flow = InstalledAppFlow.from_client_secrets_file("Credenciais.json", SCOPES)
creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')

# Salvar o token gerado
with open("token.json", "w") as token_file:
    token_file.write(creds.to_json())

print("Token gerado com sucesso!")