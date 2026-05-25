# Hello World — Agent Harness

Projeto didático que implementa os 12 componentes de um agent harness em produção, descritos no artigo "The Anatomy of an Agent Harness".

## Estrutura

```
hello-world-harness/
├── main.py      → Ponto de entrada + loop interativo com o usuário
├── harness.py   → Orchestration loop + guardrails + verificação
├── memory.py    → Memória de curto e longo prazo
├── tools.py     → Definição e execução das 4 ferramentas
└── memoria.json → Criado automaticamente para persistência
```

## Mapeamento: componente do artigo → arquivo

| # | Componente | Onde está |
|---|-----------|-----------|
| 1 | Orchestration Loop | `harness.py` → `rodar_agente()` |
| 2 | Tools | `tools.py` → `TOOL_SCHEMAS` + `executar_ferramenta()` |
| 3 | Memory | `memory.py` → classe `Memoria` |
| 4 | Context Management | `memory.py` → `compactar_se_necessario()` |
| 5 | Prompt Construction | `harness.py` → `client.messages.create()` |
| 6 | Output Parsing | `harness.py` → `classificar_resposta()` |
| 7 | State Management | `memory.py` → `salvar_notas()` |
| 8 | Error Handling | `harness.py` → try/except em todo o loop |
| 9 | Guardrails | `harness.py` → `guardrail_entrada()` + `guardrail_saida()` |
| 10 | Verification Loops | `harness.py` → `verificar_resultado_ferramenta()` |
| 11 | Subagent Orchestration | (não implementado — single-agent é o ponto de partida) |
| 12 | System Prompt | `harness.py` → constante `SYSTEM_PROMPT` |

## Como rodar

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar API key
export ANTHROPIC_API_KEY="sua-chave-aqui"

# 3. Rodar
python main.py
```

## Ferramentas disponíveis

| Ferramenta | O que faz |
|-----------|----------|
| `calcular` | Avalia expressões matemáticas Python |
| `salvar_nota` | Salva nota em arquivo JSON (persiste entre sessões) |
| `ler_notas` | Lista todas as notas salvas |
| `hora_atual` | Retorna data e hora do sistema |

## Exemplos para testar

```
Você: Quanto é raiz quadrada de 144 mais 50 dividido por 2?
Você: Salve uma nota com título "aprendizado" e conteúdo "o harness é a infraestrutura ao redor do LLM"
Você: Que horas são agora?
Você: Mostre minhas notas salvas
Você: Qual a data de hoje e quanto é 365 dividido por 7?
```

## O que observar ao rodar

Cada turno do loop imprime:
```
  [Loop] Turno 1/10
  [Ferramenta] Chamando 'calcular' com {'expressao': '...'}
  [Memória] Histórico: 3 mensagens | Notas salvas: 1
```

Isso deixa o loop de orquestração visível — você vê exatamente quando o modelo decide usar uma ferramenta, o que executa, e como o resultado volta para o contexto.
