# AgileMind · Agente de Análise de Squads

**by Júlio Cesar de Souza Silva**

Agente especialista em Agilidade para análise de reports de squads via PDF.

## Setup

```bash
cd ~/dev/Agentes\ de\ IA/chat_analise_squads
pip install -r requirements.txt
```


## Subir ambiente venv

```bash
cd ~/caminho/pdf_chat_app
source venv/bin/activate
python3 app.py
```

## .env -- substituir pela chave_API que vai se conectar
```
ANTHROPIC_API_KEY=sk-ant-...
VOYAGE_API_KEY=pa-...
```

## Executar
```bash
python app.py
# Acesse: http://localhost:5000
```

## O que o AgileMind faz
- Indexa PDFs de reports de squad via RAG (VoyageAI + Claude)
- Responde perguntas sobre o conteúdo do report
- Gera gráficos interativos (burndown, velocity) em Chart.js
- Identifica impedimentos, dívida técnica e riscos
- Cria resumos executivos para liderança
- Sugestões para retrospectiva
