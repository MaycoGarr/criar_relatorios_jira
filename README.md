# Relatórios Jira — UISA

Aplicação web local para gerar relatórios de cards do Jira, filtrar por hierarquia e etapa, e enviar por e-mail SMTP.

---
<img width="1399" height="872" alt="image" src="https://github.com/user-attachments/assets/7078d42f-9ba4-485e-be5c-bd81a9fa37b6" />


<img width="1890" height="2432" alt="image" src="https://github.com/user-attachments/assets/6d7ac269-c0dc-4d73-9bcd-49f6f2e5d2fd" />





## Funcionalidades

| Recurso | Descrição |
|---------|-----------|
| **Relatório visual** | Cards agrupados por etapa, com desenvolvedor, impeditivo e dias sem atualização |
| **Filtros** | Card pai, projeto, etapas e presets salvos |
| **E-mail HTML** | Template responsivo com pré-visualização na interface |
| **Modos de envio** | Relatório completo ou somente impeditivos |
| **Conexões CRUD** | Múltiplas contas Jira e SMTP, com padrão configurável |
| **Exportação** | `.txt` e `.html` |
| **Agendamento** | Script CLI para o Agendador de Tarefas do Windows |

---

## Início rápido

```powershell
# 1. Clonar e entrar na pasta
git clone https://github.com/MaycoGarr/criar_relatorios_jira.git
cd criar_relatorios_jira

# 2. Ambiente virtual e dependências
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 3. Variáveis de ambiente (opcional — também cadastra pela interface)
copy .env.example .env

# 4. Iniciar
run.bat
```

Abra **http://127.0.0.1:5050**

---

## Fluxo de uso

```
Conexão Jira → Filtros (card pai + etapas) → Gerar relatório → Exportar ou enviar e-mail
```

1. Cadastre uma **conexão Jira** (URL, e-mail, token de API)
2. Selecione o **card pai** e as **etapas** desejadas
3. Gere o relatório e visualize nas abas **Relatório** ou **E-mail**
4. Exporte ou envie — modo **Somente impeditivos** cancela o envio se não houver bloqueios

---

## O que cada card exibe

- Etapa (status)
- Nome, desenvolvedor responsável e flag impeditivo
- Dias sem atualização e link direto no Jira
- Última atualização relevante (comentário manual; ignora ruído de assignee/flag)

---

## Configuração

### Pré-requisitos

- Python 3.11+
- Conta Atlassian com token de API
- Conta SMTP (ex.: Office 365)

### Variáveis `.env`

| Variável | Exemplo |
|----------|---------|
| `JIRA_BASE_URL` | `https://sua-empresa.atlassian.net` |
| `JIRA_EMAIL` | `seu-email@empresa.com` |
| `JIRA_API_TOKEN` | Token gerado em [Atlassian](https://id.atlassian.com/manage-profile/security/api-tokens) |
| `SMTP_HOST` | `smtp.office365.com` |
| `SMTP_PORT` | `587` |
| `SMTP_USERNAME` | E-mail do remetente |
| `SMTP_PASSWORD` | Senha ou senha de app (MFA) |
| `SMTP_FROM_EMAIL` | Remetente exibido no e-mail |
| `SMTP_DEFAULT_RECIPIENTS` | Destinatários padrão (vírgula) |

> Credenciais também podem ser cadastradas pela interface. Arquivos em `data/` **não são versionados**.

### SMTP — Office 365

| Campo | Valor |
|-------|-------|
| Host | `smtp.office365.com` |
| Porta | `587` |
| TLS | STARTTLS |

---

## Envio agendado

```powershell
.venv\Scripts\python send_report_cli.py --mode impeditive_only
```

Usa as conexões padrão salvas em `data/`. Logs em `data/email_logs.json`.

---

## Estrutura do projeto

```
├── app.py                 # API Flask + servidor web
├── report_builder.py      # Lógica do relatório
├── report_template.py     # HTML do relatório
├── email_template.py      # HTML do e-mail
├── jira_client.py         # Cliente Jira REST
├── credentials_store.py   # CRUD conexões Jira
├── email_store.py         # CRUD conexões SMTP
├── email_sender.py        # Envio SMTP
├── filter_store.py        # Presets de filtros
├── send_report_cli.py     # Envio via linha de comando
├── static/                # Interface web
├── data/                  # Dados locais (gitignored)
├── run.bat                # Atalho de inicialização
└── requirements.txt
```

---

## JQL gerada

```jql
project = "GERAL4AT" AND parent = GERAL4AT-17 AND status IN ("Mapeamento", "Desenvolvimento", ...)
```

---

## Segurança

- `.env` e `data/*.json` ficam apenas na máquina local
- Nunca commite tokens, senhas ou credenciais
- Contas com MFA no Office 365 podem exigir senha de app no Azure AD

---

## Licença

Uso interno — Quality / UISA.
