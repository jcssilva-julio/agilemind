# Plano de Testes — AgileMind Cloud

> **Fonte da verdade do TDD.** Estes casos descrevem o **estado-alvo** após a
> migração (Railway + Supabase + autenticação), **não** o app local atual.
> Escrevemos o teste primeiro, depois o código que o faz passar.
>
> Extraído de `Plano_de_Testes_AgileMind_Cloud.docx`.

## Arquitetura-alvo (resumo)

- **Backend**: Flask hospedado no **Railway** (serve API + `index.html`, sem frontend separado).
- **Banco**: **Supabase Postgres** — usuários, sessões, metadados, chunks e embeddings.
- **Storage**: **Supabase Storage** (bucket privado) para os PDFs originais.
- **Busca**: `cosine_sim` em Python lendo chunks/embeddings do Postgres (sem pgvector nesta fase).
- **Auth**: Supabase Auth + **senha master** (só quem tem a master cria usuários; não há self-signup).
- **Visibilidade**: cada documento é `private` (só o dono) ou `public` (qualquer autenticado).

### Fora de escopo desta fase
pgvector · frontend separado (Vercel/SPA) · recuperação de senha.

## Modelo de dados (Supabase Postgres)

| Tabela | Campos principais |
|---|---|
| `auth.users` (nativa) | id, email, encrypted_password, created_at |
| `profiles` | user_id (FK), nome, created_by_master_at |
| `documents` | id, owner_user_id (FK), alias, filename, storage_path, **visibility** (private\|public), created_at |
| `document_chunks` | id, document_id (FK), chunk_index, content (text), embedding (jsonb ou float[]) |

`documents` é a peça central das regras de visibilidade — upload, listagem, chat e exclusão dependem de `visibility` e `owner_user_id`.

---

## 3. Autenticação e senha master

### 3.1 Criação de usuário via senha master
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| AUTH-01 | Criar usuário com senha master correta | POST /admin/create-user com {master_password, email, password, nome} válidos | 201. Usuário criado no Auth e em `profiles`. Senha master não retorna em nenhuma resposta. |
| AUTH-02 | Senha master incorreta | Mesma chamada com master_password errada | 401. Nenhum usuário criado. Mensagem genérica. |
| AUTH-03 | Sem enviar senha master | Campo master_password ausente | 400. Nenhum usuário criado. |
| AUTH-04 | E-mail já existente | Senha master correta, e-mail já cadastrado | 409. Nenhum novo registro. |
| AUTH-05 | E-mail inválido | Senha master correta, e-mail mal formatado (`abc@`) | 400. Validação antes de chamar o Supabase. |
| AUTH-06 | Senha fraca | Senha master correta, senha < 6 caracteres | 400. Mensagem de requisito mínimo. |
| AUTH-07 | Rota exige HTTPS em produção | Acessar via HTTP puro no Railway | Redireciona p/ HTTPS ou bloqueia. |
| AUTH-08 | Senha master nunca em logs | Inspecionar logs após AUTH-01..06 | Nenhuma ocorrência em texto plano. |
| AUTH-09 | Senha master fora do código | Verificar origem do valor | Vem de variável de ambiente (Railway), nunca hardcoded. |

### 3.2 Login
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| AUTH-10 | Login com credenciais válidas | POST /login com e-mail e senha de usuário do AUTH-01 | 200. Retorna sessão/token válido. |
| AUTH-11 | Senha incorreta | E-mail válido, senha errada | 401. Mensagem genérica ("credenciais inválidas"). |
| AUTH-12 | E-mail inexistente | E-mail nunca cadastrado | 401. Mesma mensagem do AUTH-11. |
| AUTH-13 | Campos vazios | {email:"", password:""} | 400. |
| AUTH-14 | Sem self-signup público | Verificar que não há rota de registro público | Só /admin/create-user com senha master. |
| AUTH-15 | Rate limiting de login | 10 tentativas erradas em sequência | **Bloqueio após 5 tentativas** (janela ~15 min). |

### 3.3 Sessão e proteção de rotas
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| AUTH-16 | /upload sem auth | Chamada sem sessão | 401. Upload não processado. |
| AUTH-17 | /chat sem auth | Chamada sem sessão | 401. |
| AUTH-18 | /pdf/indices sem auth | Chamada sem sessão | 401. |
| AUTH-19 | /pdf/load sem auth | Chamada sem sessão | 401. |
| AUTH-20 | /pdf/delete sem auth | Chamada sem sessão | 401. |
| AUTH-21 | / sem sessão | GET / sem cookie/token | Redireciona p/ login, não renderiza o chat. |
| AUTH-22 | Sessão expirada | Token/cookie expirado em rota protegida | 401, força novo login. |
| AUTH-23 | Logout encerra sessão | POST /logout, depois repetir AUTH-16 com mesmo cookie | 401 na tentativa seguinte. |
| AUTH-24 | Token de outro usuário | Capturar sessão de A, usar identificando-se como B | Sistema identifica pelo token, nunca por campo do payload. |

### 3.4 Gestão de usuários pós-criação (decisão #5 — só via senha master)
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| AUTH-25 | Desativar usuário via senha master | POST /admin/deactivate-user com {master_password, email} válidos | 200. Usuário marcado como inativo. Senha master não vaza. |
| AUTH-26 | Usuário desativado não consegue logar | Login com credenciais de um usuário desativado no AUTH-25 | 401. Mensagem genérica; sessão não é criada. |

## 4. Upload e classificação (migrado + visibilidade)

### 4.1 Upload básico (regressão)
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| UP-01 | PDF ágil/TI, autenticado | POST /upload, sessão válida, visibility=private | SSE progresso (extract, classify, chunk, embed) até `done`. PDF no Storage. Linha em `documents` com owner correto. |
| UP-02 | PDF fora de escopo | POST /upload com PDF não-TI | SSE `rejected`. Nada no Storage. Nenhuma linha em `documents`. |
| UP-03 | Arquivo não PDF | Enviar .docx ou .txt | 400 "Apenas PDFs são aceitos". Sem classificação/Storage. |
| UP-04 | Sem arquivo | POST /upload sem campo file | 400. |
| UP-05 | PDF sem texto (escaneado) | PDF de imagem pura | SSE `error` "PDF sem texto extraível". |
| UP-06 | Excede 50MB | Arquivo de 60MB | Rejeitado antes de processar (MAX_CONTENT_LENGTH). |
| UP-07 | Falha na classificação (Anthropic down) | Simular exceção no classificador | **Bloquear (fail-closed):** SSE emite `error`/`rejected`; nada persiste. Muda o `except: return True` atual. |

### 4.2 Visibilidade (novo)
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| UP-08 | Pergunta de visibilidade exibida | Iniciar upload de PDF válido | Frontend pergunta "todos podem ver, ou só você?" com 2 opções. |
| UP-09 | Marcado como privado | Selecionar "só por você" | `visibility='private'`, owner = usuário logado. |
| UP-10 | Marcado como público | Selecionar "todos podem ver" | `visibility='public'`. |
| UP-11 | Sem escolher visibilidade | Tentar enviar sem responder | Não prossegue (frontend bloqueia ou backend rejeita sem o campo). |
| UP-12 | Alterar visibilidade após indexado | PATCH em rota de atualização, pelo dono | Troca private↔public sem reindexar. |
| UP-13 | B altera visibilidade de doc de A | Mesma chamada do UP-12, B não é owner | 403. |

## 5. Chat / RAG (isolamento de visibilidade)
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| CHAT-01 | Doc privado próprio | A ativa seu doc privado e pergunta | RAG normal, streaming token a token. |
| CHAT-02 | Doc privado de outro | B tenta /pdf/load doc privado de A | **404** (tratado como inexistente). Não carrega. |
| CHAT-03 | Doc público de outro | B carrega doc público de A | Permitido. RAG normal. |
| CHAT-04 | Pergunta fora de escopo | Algo não-TI com doc carregado | Recusa padrão do SYSTEM_PROMPT. |
| CHAT-05 | Sem documento carregado | /chat sem upload/load antes | 400 "Nenhum report indexado...". Isolado por usuário (não global). |
| CHAT-06 | Pedido de gráfico | Pergunta pedindo burndown | Resposta com bloco HTML + Chart.js. |
| CHAT-07 | Dois usuários simultâneos | A com doc X, B com doc Y, perguntando juntos | Cada resposta usa só o doc certo. **Teste crítico** da remoção do `app_state` global. |

## 6. Gestão de relatórios indexados
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| MNG-01 | Listar p/ usuário A | GET /pdf/indices autenticado como A | Privados de A + todos os públicos. **FALHA se um privado de outro dono aparecer na lista** (regra primária de visibilidade). |
| MNG-02 | Listar sem nada | Usuário novo, sem uploads nem públicos | Lista vazia. |
| MNG-03 | Carregar doc próprio | A carrega doc que subiu | 200, ativa na sessão. |
| MNG-04 | Carregar público de outro | B carrega doc público de A | 200, ativa. |
| MNG-05 | Carregar privado de outro | B força /pdf/load em privado de A manipulando id | **404** (inexistente p/ B). Não ativa. |
| MNG-06 | Excluir doc próprio | A exclui /pdf/delete doc que subiu | Confirma antes. Remove do Storage, Postgres (`documents`+`document_chunks`) e da lista. |
| MNG-07 | Excluir doc de outro | B tenta excluir doc cujo owner é A | 403. Nada removido. |
| MNG-08 | Excluir público de outro | B tenta excluir público sem ser dono | 403. Público dá leitura, não exclusão. |

## 7. Infraestrutura e deploy (Railway + Supabase)
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| INF-01 | Env vars no Railway | Verificar ANTHROPIC_API_KEY, VOYAGE_API_KEY, SUPABASE_URL, SUPABASE_KEY, MASTER_PASSWORD, FLASK_SECRET_KEY | Todas no painel, nenhuma commitada. |
| INF-02 | App responde publicamente | Acessar URL pública do Railway | Tela de login (não o chat direto) — confirma AUTH-21. |
| INF-03 | Conexão Postgres no boot | Iniciar serviço | Sem erros de conexão nos logs. |
| INF-04 | Storage funcional | Upload de teste em produção | Arquivo aparece no bucket. |
| INF-05 | Limite do plano gratuito | Verificar consumo no painel | Documentar limite (checagem manual periódica). |
| INF-06 | Bucket é privado | Acessar URL direta de arquivo sem auth | Negado; só via backend autenticado. |
| INF-07 | HTTPS obrigatório | Acesso HTTP simples à URL | Railway força HTTPS (confirmar). |

## 8. Segurança e regressão geral
| ID | Cenário | Passos | Resultado esperado |
|----|---------|--------|--------------------|
| SEC-01 | SQL injection | `alias`/`question` com SQL malicioso | Sem efeito; queries parametrizadas. |
| SEC-02 | XSS no alias | Upload com alias `<script>` | Frontend escapa ao renderizar (`escapeHtml` já existe — confirmar cobertura). |
| SEC-03 | CORS | Chamar API de domínio não autorizado | Bloqueado, se restringir CORS (avaliar necessidade — mesmo domínio). |
| SEC-04 | Master não loga como usuário | Login em /login usando a senha master | 401. Master só vale em /admin/create-user. |
| SEC-05 | Fluxo feliz completo | Criar via master → login → subir privado → perguntar → subir público → login 2º user → vê público, não vê privado → tenta excluir público (falha) → exclui privado original (ok) | Tudo em sequência sem erros, replicando seções 3–6 ponta a ponta. |

---

Ver decisões em aberto em [DECISOES_PENDENTES.md](DECISOES_PENDENTES.md).
