# Testes (TDD)

Esta pasta é a **fonte da verdade** do desenvolvimento. Os casos de teste vêm
primeiro; o código é escrito depois para fazê-los passar.

## Onde colocar o quê

| O quê | Onde | Convenção |
|---|---|---|
| Casos de teste automatizados | `tests/test_*.py` | uma função `test_...` por caso |
| Cenários / casos em texto (rascunho) | `tests/casos_de_teste.md` | tabela: ID, cenário, entrada, esperado |
| Dados de apoio (PDFs, JSONs) | `tests/fixtures/` | arquivos de exemplo |
| Configuração compartilhada | `tests/conftest.py` | fixtures do pytest |

## Como rodar

```bash
pip install pytest
pytest -q
```

## Fluxo TDD que vamos seguir

1. Você descreve os **casos de teste** (aqui, em `.md` ou `.py`).
2. Eu transformo em **especificação + plano de desenvolvimento**.
3. Escrevemos os testes (vermelho 🔴) e depois o código até passar (verde 🟢).
