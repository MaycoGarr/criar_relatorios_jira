# Relatório Jira — UISA

Aplicação web para gerar relatórios de cards do Jira com filtros por espaço, hierarquia (card pai) e etapas, com envio por e-mail SMTP.

## O que o relatório exibe

Para cada card filho do pai informado:

1. Etapa (status)
2. Nome do card, desenvolvedor responsável e flag impeditivo
3. Dias sem atualização e link direto do card no Jira
4. Última atualização (comentário manual prioritário; ignora ruído de assignee/flag)

## Pré-requisitos

- Python 3.11+
- Conta Atlassian com acesso ao Jira
- Token de API do Atlassian
- Conta SMTP (ex.: Office 365) para envio de e-mails

## Configuração

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Edite o `.env` com credenciais Jira e SMTP (opcional — também pode cadastrar pela interface).

## Executar

```bash
run.bat
```

ou:

```bash
python app.py
```

Abra: [http://127.0.0.1:5050](http://127.0.0.1:5050)

## Conexões Jira (CRUD)

Credenciais em `data/credentials.json` (não versionado).

- **Gerenciar conexões** — criar, editar, excluir, definir padrão
- Importação automática do `.env` na primeira execução

## Conexões de e-mail SMTP (CRUD)

Credenciais em `data/email_connections.json` (não versionado).

| Campo | Valor sugerido (Office 365) |
|-------|----------------------------|
| SMTP | `smtp.office365.com` |
| Porta | `587` |
| TLS | STARTTLS ativado |
| Remetente | `processosautomatizados@quality.com.br` |

Na interface:

1. **Gerenciar e-mails** — CRUD completo
2. **Testar envio** — valida SMTP com destinatários informados
3. **Enviar por e-mail** — gera e envia o relatório

### Modos de relatório

- **Relatório completo** — todos os cards filtrados
- **Somente impeditivos** — ideal para alertas por e-mail (padrão)

Se não houver impeditivos no modo "Somente impeditivos", o envio é cancelado com aviso na interface.

### Assunto do e-mail

Exemplo: `[UISA] 4 impeditivo(s) — Relatório Jira 02/07/2026 08:55`

## Filtros

- **Card pai:** dropdown com chave e nome (`GERAL4AT-17 — UISA`)
- Filtros carregados automaticamente ao trocar conexão Jira ou projeto
- Exportação `.txt` e `.html`

### Layout do e-mail

O envio utiliza um template HTML dedicado (`email_template.py`) com visual Apple-like:

- Fundo cinza claro, cards brancos com bordas arredondadas
- Tipografia system-ui (San Francisco / Segoe UI)
- Badges de impeditivo, botão "Abrir no Jira" e resumo no topo

Na interface, use a aba **E-mail** para pré-visualizar antes de enviar.

## Envio agendado (fase 2)

Use o script CLI com o Agendador de Tarefas do Windows:

```bash
.venv\Scripts\python send_report_cli.py --mode impeditive_only
```

O script usa as conexões padrão salvas em `data/`. Logs de envio em `data/email_logs.json`.

## Webhook (fase 2)

O campo **Webhook URL** nas conexões de e-mail está reservado para integração futura com Power Automate, n8n ou Teams, sem alterar a geração do relatório.

## JQL gerada

```jql
project = "GERAL4AT" AND parent = GERAL4AT-17 AND status IN ("Mapeamento", "Desenvolvimento", ...)
```

## Observações

- Porta 587 + STARTTLS é recomendada para Office 365 (porta 25 costuma ser bloqueada)
- Contas com MFA podem exigir senha de app no Azure AD
- Credenciais ficam apenas em arquivos locais fora do git
