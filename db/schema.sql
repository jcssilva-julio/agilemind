-- =====================================================================
-- AgileMind Cloud — schema Supabase (Postgres)
-- Rode no SQL Editor do Supabase (uma vez). auth.users é nativa do Auth.
-- =====================================================================

-- Perfis (1:1 com auth.users). is_active habilita desativação (AUTH-25/26).
create table if not exists profiles (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  nome       text,
  is_active  boolean not null default true,
  created_by_master_at timestamptz not null default now()
);

-- Documentos: peça central das regras de visibilidade.
create table if not exists documents (
  id            uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references auth.users(id) on delete cascade,
  alias         text not null,
  filename      text not null,
  storage_path  text not null,
  visibility    text not null check (visibility in ('private','public')),
  created_at    timestamptz not null default now()
);
create index if not exists idx_documents_owner on documents(owner_user_id);
create index if not exists idx_documents_visibility on documents(visibility);

-- Chunks + embeddings (substitui o pickle local). Sem pgvector nesta fase.
create table if not exists document_chunks (
  id          uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  chunk_index int  not null,
  content     text not null,
  embedding   jsonb not null
);
create index if not exists idx_chunks_document on document_chunks(document_id);

-- Sessões server-side: permitem invalidar no logout e expirar de verdade.
create table if not exists sessions (
  token      text primary key,
  user_id    uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null
);
create index if not exists idx_sessions_user on sessions(user_id);

-- Observação sobre RLS:
-- O backend acessa o banco com a SERVICE_ROLE key (que ignora RLS) e aplica
-- todas as permissões em código (visibilidade, dono, etc.). Habilitar RLS como
-- defesa em profundidade fica para uma fase futura.
