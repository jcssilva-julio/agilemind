# Decisões (FECHADAS em 2026-06-22)

> Seção 9 do plano. Todas as pendências foram decididas com Júlio.
> As decisões abaixo já estão refletidas em `casos_de_teste.md` e nos `test_*.py`.

| # | Caso afetado | Decisão | Observação |
|---|---|---|---|
| 1 | UP-07 | **Bloquear (restritivo)** | Se a classificação (Anthropic) falhar em produção, o upload é **recusado**. Muda o `except: return True` atual para fail-closed. |
| 2 | AUTH-15 | **5 tentativas** → bloqueio temporário | Janela de bloqueio sugerida: 15 min. |
| 3 | MNG-05 / CHAT-02 | **404** no acesso direto | Doc privado de outro usuário: tratado como inexistente. Ver também reforço do MNG-01 (lista). |
| 4 | Recuperação de senha | **Fica para depois** | Fora de escopo desta fase. Reset manual via senha master por enquanto. |
| 5 | Gestão de usuários pós-criação | **Só via senha master** | Mesma master cria e desativa/remove, via rota /admin protegida. Ver AUTH-25/26. |

## Ajuste de caso de teste (apontado por Júlio)

A regra de visibilidade tem **duas camadas** e os testes devem cobrir ambas:

1. **Listagem (primária):** um documento privado do usuário A **não pode**
   aparecer na lista do usuário B. → MNG-01 (reforçado: falha se aparecer).
2. **Acesso direto (secundária):** mesmo manipulando o id, B não acessa
   privado de A. → MNG-05 / CHAT-02 retornam **404**.

## Status
- [x] 1 — UP-07: bloquear
- [x] 2 — AUTH-15: N=5
- [x] 3 — MNG-05/CHAT-02: 404 + reforço MNG-01
- [x] 4 — recuperação de senha: depois
- [x] 5 — gestão de usuários: só via senha master
