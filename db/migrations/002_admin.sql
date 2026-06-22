-- =====================================================================
-- AgileMind Cloud — migração 002: Camada de Administração (v2)
-- Rode no SQL Editor do Supabase. Idempotente (IF NOT EXISTS / DO blocks).
-- =====================================================================

-- profiles: papel (role) + autoria (created_by) + data de criação --------
alter table profiles add column if not exists created_at timestamptz not null default now();
alter table profiles add column if not exists role text not null default 'user';
do $$ begin
  if not exists (select 1 from pg_constraint where conname = 'profiles_role_check') then
    alter table profiles add constraint profiles_role_check check (role in ('admin','user'));
  end if;
end $$;
alter table profiles add column if not exists created_by uuid references auth.users(id) on delete set null;

-- document_chunks: registrar o modelo de embeddings usado --------------
alter table document_chunks add column if not exists embedding_model text;

-- admin_audit_log: trilha de auditoria das ações administrativas -------
create table if not exists admin_audit_log (
  id                 uuid primary key default gen_random_uuid(),
  actor_user_id      uuid references auth.users(id) on delete set null,
  action             text not null,
  target_user_id     uuid references auth.users(id) on delete set null,
  target_document_id uuid,
  details            jsonb,
  created_at         timestamptz not null default now()
);
create index if not exists idx_audit_actor on admin_audit_log(actor_user_id);
create index if not exists idx_audit_created on admin_audit_log(created_at desc);

-- app_config: parâmetros editáveis em runtime (ex.: modelo de IA) ------
create table if not exists app_config (
  key        text primary key,
  value      text not null,
  updated_by uuid references auth.users(id) on delete set null,
  updated_at timestamptz not null default now()
);
