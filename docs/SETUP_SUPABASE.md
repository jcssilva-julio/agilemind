# Setup do Supabase — passo a passo (Fase 0)

Tempo estimado: ~10 min. Tudo no plano gratuito.

## 1. Criar conta e projeto
1. Acesse https://supabase.com e entre com GitHub (ou e-mail).
2. **New project** → escolha a organização.
3. Preencha:
   - **Name:** `agilemind`
   - **Database Password:** gere uma forte e **guarde** (é a senha do Postgres).
   - **Region:** a mais próxima (ex.: `South America (São Paulo)`).
4. **Create new project** e aguarde ~2 min o provisionamento.

## 2. Pegar as credenciais (URL + keys)
Menu lateral: **Project Settings (⚙️) → API**. Copie:
- **Project URL** → vira `SUPABASE_URL`
- **Project API keys → `service_role` (secret)** → vira `SUPABASE_KEY`

> ⚠️ Use a **service_role**, não a `anon`. O backend precisa de privilégio para
> criar usuários (senha master) e ler/gravar ignorando RLS. **Ela é secreta:**
> fica só no `.env` (já ignorado pelo git) e nas envs do Railway. Nunca no front.

## 3. Criar as tabelas
1. Menu lateral: **SQL Editor → New query**.
2. Cole todo o conteúdo de [`db/schema.sql`](../db/schema.sql).
3. **Run**. Deve criar `profiles`, `documents`, `document_chunks`, `sessions`.
4. Confira em **Table Editor** que as 4 tabelas apareceram.

## 4. Criar o bucket de Storage (privado)
1. Menu lateral: **Storage → New bucket**.
2. **Name:** `documents`
3. **Public bucket:** deixe **DESmarcado** (privado — requisito INF-06).
4. **Create bucket**.

## 5. Preencher o `.env` local
Adicione ao seu `.env` (que já existe com as chaves de IA):
```
SUPABASE_URL=...        # passo 2
SUPABASE_KEY=...        # service_role do passo 2
MASTER_PASSWORD=...     # você escolhe — habilita criar/desativar usuários
FLASK_SECRET_KEY=...    # string aleatória longa (ex.: openssl rand -hex 32)
```
Gerar um FLASK_SECRET_KEY no terminal:
```bash
openssl rand -hex 32
```

## 6. (Opcional agora) Primeiro usuário
A criação de usuários será pela rota `/admin/create-user` (senha master), que
implementamos na Fase 1. Não precisa criar usuário manualmente no painel.

---

## Checklist para me avisar que está pronto
- [ ] Projeto Supabase criado
- [ ] `SUPABASE_URL` e `SUPABASE_KEY` (service_role) no `.env`
- [ ] `db/schema.sql` rodado (4 tabelas criadas)
- [ ] Bucket privado `documents` criado
- [ ] `MASTER_PASSWORD` e `FLASK_SECRET_KEY` no `.env`

Quando marcar tudo, me diz que eu sigo. **Enquanto isso, posso adiantar as
Fases 0 e 1 com repositórios *fake*** (sem rede), então não fica bloqueado.
