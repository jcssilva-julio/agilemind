# Plano de Desenvolvimento — AgileMind Cloud

> Objetivo: sair do estado atual (Flask local, `app_state` global, persistência em
> pickle, sem auth) para o estado-alvo (Railway + Supabase + auth/senha master +
> visibilidade + isolamento por usuário), **fazendo passar os 66 casos** de
> `tests/casos_de_teste.md`, em TDD (red → green, fase a fase).

## Decisões já fechadas (de `tests/DECISOES_PENDENTES.md`)
- UP-07: classificador **fail-closed** (falhou → bloqueia).
- AUTH-15: rate limit **5 tentativas** / ~15 min.
- Acesso a privado de outro: **404** (lista + acesso direto).
- Recuperação de senha: fora desta fase.
- Gestão de usuários: **só via senha master**.

---

## Arquitetura e decisões técnicas

### Camadas (refatoração do `app.py` monolítico)
```
app.py            -> bootstrap Flask, registro de blueprints
config.py         -> envs (ANTHROPIC/VOYAGE/SUPABASE/MASTER_PASSWORD/FLASK_SECRET_KEY)
db/supabase.py    -> cliente Supabase (Postgres + Storage)
repositories/     -> acesso a dados (users, documents, chunks, sessions)
services/         -> rag.py (embed/retrieve/stream), classifier.py, storage.py
auth/             -> rotas de auth, senha master, decorator @login_required
routes/           -> upload, chat, reports (pdf/*)
```
A **camada de repositório** é o ponto-chave para o TDD: os testes injetam *fakes*
(sem rede) para casos de unidade/rota; um punhado de testes de integração (INF-*)
roda contra um Supabase de teste real.

### Sessão / autenticação
- Login valida credenciais via **Supabase Auth** (`sign_in_with_password`).
- Sessão **server-side**: token de sessão guardado numa tabela `sessions`
  (cookie httpOnly só carrega o id). Isso permite **invalidação real no logout**
  (AUTH-23) e **expiração** (AUTH-22) — o que um cookie assinado stateless não dá.
- Usuário é sempre identificado pelo token da sessão, **nunca** por campo do
  payload (AUTH-24).

### Senha master
- Vem de `MASTER_PASSWORD` (env do Railway), nunca hardcoded (AUTH-09).
- Só habilita `/admin/*` (criar/desativar usuário). Não serve para login (SEC-04).
- Nunca logada (AUTH-08): filtro de logging + nunca ecoar em respostas.

### Persistência (substitui pickle/uploads locais)
- `documents` (metadados + `owner_user_id` + `visibility`) e `document_chunks`
  (conteúdo + embedding em jsonb) no **Postgres**.
- PDF original no **Supabase Storage** (bucket **privado**, INF-06).
- `cosine_sim` (já existe) passa a ler chunks/embeddings do Postgres. Sem pgvector.

### Isolamento por usuário (fim do `app_state` global)
- O "documento ativo" deixa de ser global e passa a ser **por sessão** (CHAT-07).

### Dependências novas (`requirements.txt`)
`supabase`, `gunicorn` (servidor de produção), `Flask-Limiter` (rate limit),
`email-validator` (validação de e-mail).

---

## Fases de desenvolvimento

Cada fase: **destravar** os testes da fase (remover `skip`) → rodar (vermelho) →
implementar → verde → commit.

### Fase 0 — Fundação (infra + harness de teste)
Sem isto nada compila contra o Supabase.
- `config.py`, `db/supabase.py`, camada `repositories/` com interface + *fake* p/ testes.
- Migrations SQL: `profiles`, `documents`, `document_chunks`, `sessions`.
- Bucket privado no Storage.
- `conftest.py`: fixtures de cliente autenticado, usuários A/B, *mocks* de
  Anthropic/Voyage (respostas determinísticas).
- **Cobre/prepara:** base de dados de todos os testes; INF-03, INF-04, INF-06 (parcial).

### Fase 1 — Autenticação e senha master
- `POST /admin/create-user` (valida master, formato de e-mail, senha ≥6, duplicado).
- `POST /login`, `POST /logout` (sessão server-side).
- `POST /admin/deactivate-user`.
- Sem self-signup público. Rate limit no login. Master fora dos logs.
- **Cobre:** AUTH-01..06, 08, 09, 10..15, 25, 26; SEC-04.

### Fase 2 — Proteção de rotas e sessão
- Decorator `@login_required`; `before_request` nas rotas protegidas.
- `/` redireciona para login sem sessão; expiração e logout invalidam de verdade.
- **Cobre:** AUTH-07*, 16..24. (*AUTH-07 HTTPS finaliza na Fase 7.)

### Fase 3 — Upload migrado (Storage + Postgres + classificador fail-closed)
- `/upload` autenticado: extrai → classifica (**bloqueia se falhar**) → chunk →
  embed → grava em `documents`/`document_chunks` + PDF no Storage. Mantém o SSE atual.
- **Cobre:** UP-01..07.

### Fase 4 — Visibilidade e gestão de relatórios
- Campo `visibility`; upload **exige** escolha (frontend + backend).
- `PATCH` de visibilidade (só dono). Listagem = próprios privados + todos públicos.
- `/pdf/load` e `/pdf/delete` com permissão: privado de outro = **404**; excluir de
  outro = **403**.
- **Cobre:** UP-08..13; MNG-01..08; CHAT-02, CHAT-03.

### Fase 5 — Chat isolado por usuário
- Remove `app_state` global; documento ativo por sessão. RAG lê do Postgres.
- Dois usuários simultâneos sem vazamento de contexto (teste crítico).
- **Cobre:** CHAT-01, 04, 05, 06, 07.

### Fase 6 — Segurança / hardening
- Queries parametrizadas (cliente Supabase), `escapeHtml` no alias (verificar/estender),
  decisão de CORS, garantir master fora de logs.
- **Cobre:** SEC-01, 02, 03; reforça AUTH-08.

### Fase 7 — Deploy Railway + verificação de infra + E2E
- `Procfile`/gunicorn, env vars no Railway, HTTPS forçado.
- Bateria INF-* em produção e o **fluxo feliz completo** SEC-05.
- **Cobre:** INF-01, 02, 05, 07; AUTH-07; SEC-05.

---

## Mapa de cobertura (todos os 66 casos)

| Fase | Casos |
|------|-------|
| 0 | (base) INF-03, INF-04, INF-06 |
| 1 | AUTH-01..06, 08, 09, 10..15, 25, 26; SEC-04 |
| 2 | AUTH-16..24 (e 07 parcial) |
| 3 | UP-01..07 |
| 4 | UP-08..13; MNG-01..08; CHAT-02, 03 |
| 5 | CHAT-01, 04, 05, 06, 07 |
| 6 | SEC-01, 02, 03 |
| 7 | INF-01, 02, 05, 07; AUTH-07; SEC-05 |

Total: **AUTH 26 + UP 13 + CHAT 7 + MNG 8 + INF 7 + SEC 5 = 66**. ✅

---

## Ordem de execução e dependências
`Fase 0` → `1` → `2` → `3` → `4` → `5` → `6` → `7`
(2 depende de 1; 3 de 0 e 2; 4 de 3; 5 de 3 e 4; 6 e 7 ao final.)

## Pré-requisitos seus (fora do código)
- Criar projeto no **Supabase** e me passar `SUPABASE_URL` + `SUPABASE_KEY`
  (vão no `.env` local, que já é ignorado pelo git).
- Definir o valor de `MASTER_PASSWORD` e um `FLASK_SECRET_KEY`.
- Conta **Railway** (só na Fase 7).
