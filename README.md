# AgileMind · Squad Intelligence

**by Júlio Cesar de Souza Silva**

Agente especialista em agilidade que analisa **reports de squads em PDF** via RAG
(VoyageAI + Claude): responde perguntas sobre o documento, gera gráficos
(burndown, velocity) e dá insights ágeis. Aplicação web **multiusuário**,
autenticada, com painel de administração — rodando em nuvem.

🔗 **Em produção:** Railway · 🗄️ **Dados:** Supabase (Postgres + Storage)

---

## O que faz

**Para o usuário**
- Upload de PDF de report de squad (privado ou público) → indexação via RAG
- Chat sobre o conteúdo: métricas, impedimentos, dívida técnica, riscos
- Geração de gráficos (burndown, velocity) em Chart.js e resumos executivos
- Guard rail: só aceita documentos de TI/agilidade (classificação automática)
- Troca da própria senha

**Para o administrador** (painel `/admin`)
- Usuários: criar, editar, promover/revogar admin, resetar senha, desativar/excluir
- Documentos: ver todos (de qualquer usuário), reindexar, excluir
- Modelo de IA configurável em runtime (Claude/Voyage), sem redeploy
- Log de auditoria de todas as ações administrativas

## Arquitetura

Flask em camadas com injeção de dependências (testável com *fakes* em memória):

```
config.py / container.py     bootstrap + injeção de dependências
auth/                        login, sessão server-side, troca de senha
admin/                       bootstrap, gestão de usuários, modelo, auditoria
routes/documents.py          upload, chat, listagem (por usuário + visibilidade)
services/                    rag, ai, storage, validações, senhas
repositories/                acesso a dados (Supabase) — profiles, documents, ...
templates/ · static/         UI (app, login, setup, admin) + componentes
db/                          schema.sql + migrações
```

- **Auth:** Supabase Auth + papéis (`admin`/`user`); senha master só para
  bootstrap/emergência. Sessão server-side (invalida no logout/expira de fato).
- **Visibilidade:** documentos `private` (só o dono) ou `public`; isolamento por
  usuário validado pelo token a cada request.

## Stack

| Camada | Tecnologia |
|---|---|
| Backend | Python + Flask (gunicorn em produção) |
| Banco / Auth / Storage | Supabase (Postgres, Auth, Storage privado) |
| IA | Claude (chat/classificação) + Voyage (embeddings) |
| Deploy | Railway |

## Rodar localmente

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # preencha as chaves (veja abaixo)
python app.py          # http://localhost:5000
```

`.env` (nunca versionado):
```
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
SUPABASE_URL=https://....supabase.co
SUPABASE_KEY=sb_secret_...      # service_role
MASTER_PASSWORD=...             # cria o 1º admin via /admin/setup
FLASK_SECRET_KEY=...            # openssl rand -hex 32
```

Primeiro acesso: abra `/admin/setup`, informe a senha master e crie o admin.
Setup do Supabase: ver [docs/SETUP_SUPABASE.md](docs/SETUP_SUPABASE.md).

## Testes

```bash
pip install pytest
pytest -q
```

Desenvolvimento guiado por testes (TDD). Ver o plano em
[docs/PLANO_DESENVOLVIMENTO.md](docs/PLANO_DESENVOLVIMENTO.md) e os casos em
[tests/](tests/).

## Deploy

Passo a passo no Railway: [docs/DEPLOY_RAILWAY.md](docs/DEPLOY_RAILWAY.md).
