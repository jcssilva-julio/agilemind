# Plano de Testes — Tipo de Documento + Multi-Squad (TYPE-01..25)

> Segunda camada de classificação (roda **após** o classificador de domínio).
> Fonte: `Document_Type_Multisquad_Final_Melhoria.pdf`.

## Decisões fechadas
- **Detecção de squad (UC-02):** via **chamada ao modelo** por trecho (`identify_squad`).
- **Correção manual do tipo:** **permitida** (PATCH `/pdf/<id>/type`, só o dono) + seletor no app.
- **Desempate CV vs report (TYPE-08):** prioriza o propósito geral (embutido no prompt do classificador).

## Modelo de dados (migração 003)
- `documents.document_type` (5 valores; default `other_it_document`).
- `document_chunks.squad_name` (null = conteúdo geral).

## Cobertura
| Faixa | Testável (automatizado) | Manual (comportamento do modelo) |
|---|---|---|
| 6.1 Classificação | TYPE-06 (fallback), TYPE-07 (ordem) | TYPE-01..05, 08 (acurácia) |
| 6.2 Chunking squad | TYPE-09, 10, 11, 12 (squad_name) | — |
| 6.3 Retrieval | TYPE-13 (filtra por squad), TYPE-17 | TYPE-14, 15, 16 (qualidade) |
| 6.4 Prompt dinâmico | TYPE-18..22 (bloco por tipo) + fallback | TYPE-20, 23 (resposta) |
| Correção manual | dono 200 · inválido 400 · outro 403 | — |
| 6.5 Regressão | — | TYPE-24, 25 (E2E manual) |

Testes automatizados em `tests/test_doctype.py` (16 passam, 4 skip de modelo/manual).

## Pipeline final
1. Domínio (`is_agile_document`) → rejeita se NÃO.
2. **Tipo** (`classify_type`) → 1 de 5; fallback `other_it_document` em falha.
3. Chunking: se `squad_report_multi`, cada chunk recebe `squad_name` (via modelo); senão null.
4. Chat: retrieval filtra por squad citada (multi) + prompt dinâmico por tipo.
