# Plano de Testes — Camada de Administração (v2)

> **Substitui**, na gestão de usuários, o desenho da Fase 1 (criação via senha
> master direta). A senha master passa a ser **só bootstrap + emergência**.
> Fonte: `Admin_v2_Caso_de_Uso_e_Testes.pdf`.

## Modelo de dados (migração 002)
- `profiles` ganha **role** (`admin`|`user`) e `created_by`.
- Nova `admin_audit_log` (actor, action, alvo, details, created_at).
- Nova `app_config` (key, value, updated_by, updated_at) — modelo de IA em runtime.
- `document_chunks` ganha `embedding_model`.

## Decisões fechadas (seção 6)
- ADM-26 (excluir usuário com docs): **bloquear** enquanto tiver documentos.
- ADM-15/23 (senha gerada): **16 caracteres**, tipos mistos, exibida 1 vez.
- ADM-35 (salvar modelo): **validar com chamada real** ao provider.
- ADM-34: **registrar `embedding_model`** por chunk.
- Login: bloqueio após **5** tentativas (vale também p/ admin).

## Reconciliação com a Fase 1
- **Substituídos** (viram bootstrap/admin): AUTH-01..06, 08, 25, 26.
- **Mantidos**: AUTH-09 (master de env), AUTH-10..24 (login/sessão/proteção), SEC-04.

---

## 5.1 Bootstrap e emergência (senha master)
| ID | Cenário | Esperado |
|----|---------|----------|
| ADM-01 | Bootstrap do 1º admin com master correta (sem admin no sistema) | 201, role=admin, created_by=null, log `bootstrap_admin` |
| ADM-02 | Bootstrap com master incorreta | 401, nada criado |
| ADM-03 | Bootstrap quando já existe admin | 403/409, recusado |
| ADM-04 | Recuperação de emergência sem admin com acesso (master correta) | reativa admin mais antigo / nova senha; log `emergency_recovery` |
| ADM-05 | Emergência com master incorreta | 401, nada alterado |
| ADM-06 | Emergência havendo admin ativo | recusada ou exige 2ª confirmação |
| ADM-07 | Master nunca em log/resposta | nenhuma ocorrência fora da env |

## 5.2 Login e controle de acesso por role
| ID | Cenário | Esperado |
|----|---------|----------|
| ADM-08 | Login de admin | 200, sessão indica role=admin, frontend mostra link do painel |
| ADM-09 | Login de usuário comum | 200, sem link do painel |
| ADM-10 | Usuário comum acessa rota admin pela URL | 403 |
| ADM-11 | Não autenticado acessa rota admin | 401 |
| ADM-12 | Admin revogado perde acesso na req seguinte (role revalidado a cada request) | 403 |

## 5.3 Administração de usuários (UC-05)
| ID | Cenário | Esperado |
|----|---------|----------|
| ADM-13 | Listar usuários | e-mail, nome, role, data, status; sem hash de senha |
| ADM-14 | Criar usuário pelo painel (senha manual) | 201, usuário loga; log com actor_user_id |
| ADM-15 | Criar usuário (senha gerada) | senha forte (16, mista) exibida 1 vez, não recuperável |
| ADM-16 | Criar com e-mail já existente | 409 |
| ADM-17 | Editar nome/e-mail | atualiza profiles+Auth; log |
| ADM-18 | Promover user→admin | vê painel no próximo refresh; log |
| ADM-19 | Revogar admin→user | perde acesso imediato; log |
| ADM-20 | Único admin tenta rebaixar a si mesmo | bloqueado (nunca ficar sem admin) |
| ADM-21 | Rebaixar a si mesmo havendo outros admins | permitido; perde acesso |
| ADM-22 | Resetar senha manual de outro usuário | atualiza Auth; invalida sessões; log |
| ADM-23 | Resetar com senha aleatória | senha forte 1 vez; invalida sessões |
| ADM-24 | Desativar usuário | não loga (401); dados/docs intactos |
| ADM-25 | Reativar usuário desativado | volta a logar |
| ADM-26 | Excluir usuário | **bloquear se tiver docs**; senão remove Auth+profiles; log antes |
| ADM-27 | Admin tenta excluir a si mesmo | bloqueado / 2ª confirmação |

## 5.4 Documentos indexados (UC-06) — DEPENDE DA FASE 3/4
| ID | Cenário | Esperado |
|----|---------|----------|
| ADM-28 | Ver todos os documentos do sistema | lista todos com metadados/dono/visibilidade |
| ADM-29 | Forçar reindexação | pipeline refeito, sobrescreve |
| ADM-30 | Reindexação falha no meio | estado anterior preservado (atômico) |
| ADM-31 | Excluir doc de qualquer usuário | removido Storage+Postgres; log |

## 5.5 Configuração de modelo de IA (UC-07)
| ID | Cenário | Esperado |
|----|---------|----------|
| ADM-32 | Ver modelo atual | claude_model/voyage_model de app_config ou fallback do código |
| ADM-33 | Alterar modelo de chat | grava em app_config; próxima /chat usa novo, sem reiniciar |
| ADM-34 | Alterar modelo de embeddings | grava; próximo upload usa novo |
| ADM-35 | Salvar modelo inválido | **valida com chamada real**; rejeita se inválido |
| ADM-36 | app_config vazia | usa fallback do código, sem erro |

## 5.6 Troca de senha pelo próprio usuário (UC-08)
| ID | Cenário | Esperado |
|----|---------|----------|
| ADM-37 | Trocar com dados corretos | 200, senha alterada no Auth |
| ADM-38 | Senha atual incorreta | 401, nada alterado |
| ADM-39 | Nova ≠ confirmação | 400, sem chamada ao Supabase |
| ADM-40 | Nova == atual | rejeitar (deve ser diferente) |
| ADM-41 | Nova fraca (<8) | 400, requisito claro |
| ADM-42 | Sessões antigas invalidadas após troca | token antigo → 401 |
| ADM-43 | Usuário comum troca a própria senha | funciona, independe de role |
| ADM-44 | Admin troca a própria senha (mesma tela) | funciona, sem rota especial |

## 5.7 Auditoria
| ID | Cenário | Esperado |
|----|---------|----------|
| ADM-45 | Toda ação admin gera log | linha com actor, action, alvo, timestamp |
| ADM-46 | Log é somente leitura | sem rota/botão de edição/exclusão |
| ADM-47 | Usuário comum não acessa auditoria | 403 |
