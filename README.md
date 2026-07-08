# 📊 Relatório Jira

Aplicação Web desenvolvida em Python para geração de relatórios do Jira, permitindo consultar cards por projeto, card pai e status, exportar os resultados e enviá-los automaticamente por e-mail.
<img width="1388" height="849" alt="image" src="https://github.com/user-attachments/assets/fc1e10cd-9da7-42b6-a22b-5a94ce53fa77" />

---

## Funcionalidades

- Consulta de cards via API do Jira
- Filtros por Projeto, Card Pai e Status
- Relatório completo ou somente impeditivos
- Exportação em HTML e TXT
- Envio de e-mail via SMTP
- Gerenciamento de múltiplas conexões Jira e SMTP
- Execução agendada via CLI

---

## Tecnologias

- Python 3.11+
- Flask
- Jira REST API
- SMTP

---

## Instalação

```bash
git clone <repositorio>
cd criar_relatorios_jira

python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env
```

---

## Executando

```bash
python app.py
```

ou

```bash
run.bat
```

Acesse:

```
http://127.0.0.1:5050
```

---

## Configuração

As conexões são armazenadas localmente:

| Arquivo | Descrição |
|----------|-----------|
| `data/credentials.json` | Conexões Jira |
| `data/email_connections.json` | Conexões SMTP |
| `data/email_logs.json` | Histórico de envios |

Na primeira execução, as configurações também podem ser importadas automaticamente do arquivo `.env`.

---

## Envio Agendado

```bash
.venv\Scripts\python send_report_cli.py --mode impeditive_only
```

---

## Estrutura

```
app.py
send_report_cli.py
email_template.py
requirements.txt

data/
templates/
static/
```

---

## Observações

- As credenciais permanecem apenas em arquivos locais.
- Utilize SMTP com STARTTLS (porta 587) para Office 365.
- Os arquivos da pasta `data/` não devem ser versionados.

---

## Licença

Projeto para uso interno.
