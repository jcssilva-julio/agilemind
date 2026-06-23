-- =====================================================================
-- AgileMind Cloud — migração 003: tipo de documento + squad por chunk
-- Rode no SQL Editor do Supabase. Idempotente.
-- =====================================================================

-- documents: segunda camada de classificação (tipo do documento)
alter table documents add column if not exists document_type text not null default 'other_it_document';

-- document_chunks: nome da squad do trecho (multi-squad); null = conteúdo geral
alter table document_chunks add column if not exists squad_name text;
