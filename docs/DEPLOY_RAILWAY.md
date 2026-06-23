# Deploy no Railway — passo a passo (Fase 7)

O código já está pronto para produção: `Procfile` (gunicorn), `wsgi.py` (ProxyFix
para HTTPS atrás do proxy) e `.python-version`. O Supabase já está configurado.

## 1. Criar o projeto
1. Acesse https://railway.app e entre com o GitHub.
2. **New Project → Deploy from GitHub repo** → selecione `jcssilva-julio/agilemind`.
3. O Railway detecta Python (Nixpacks), instala o `requirements.txt` e usa o `Procfile`.

## 2. Variáveis de ambiente (Settings → Variables)
Adicione (os mesmos valores do seu `.env` local — **nunca commitados**):
```
ANTHROPIC_API_KEY = ...
VOYAGE_API_KEY    = ...
SUPABASE_URL      = https://....supabase.co
SUPABASE_KEY      = sb_secret_...        (service_role)
MASTER_PASSWORD   = ...
FLASK_SECRET_KEY  = <novo, forte>        (openssl rand -hex 32)
```
> Gere um `FLASK_SECRET_KEY` novo para produção (não reaproveite o de dev).

## 3. Gerar o domínio
**Settings → Networking → Generate Domain**. O Railway dá uma URL pública HTTPS.

## 4. Primeiro acesso
1. Abra `https://SEU-APP.up.railway.app/admin/setup`
2. Use a `MASTER_PASSWORD` para criar o primeiro admin.
3. Faça login e use o painel `/admin` para criar os demais usuários.

---

## Checklist de verificação em produção (INF-01..07 / SEC-05)
- [ ] **INF-01** — todas as 6 variáveis presentes no painel; nenhuma no repositório.
- [ ] **INF-02** — abrir a URL pública leva à tela de **login** (não ao chat).
- [ ] **INF-03** — logs de boot sem erro de conexão com o Postgres.
- [ ] **INF-04** — fazer um upload real; o arquivo aparece no bucket do Supabase Storage.
- [ ] **INF-05** — anotar o limite do plano gratuito do Railway (checagem periódica).
- [ ] **INF-06** — tentar abrir a URL direta de um arquivo do bucket sem auth → negado.
- [ ] **INF-07** — acessar via `http://` → redireciona/forçado para `https://`.
- [ ] **SEC-05** — fluxo feliz completo (criar admin, login, subir privado, perguntar,
      subir público, logar 2º usuário, ver público mas não privado, excluir público
      falha, excluir privado funciona). *(já coberto por teste automatizado local.)*

## Observações
- `secure=not debug` nos cookies + ProxyFix garantem cookie **Secure** sob HTTPS.
- Sem self-signup: usuários só nascem por bootstrap (master) ou pelo painel admin.
- O bucket `documents` deve permanecer **privado** (criado assim na Fase 0).
