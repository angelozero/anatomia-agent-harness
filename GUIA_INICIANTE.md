# A Anatomia de um Agent Harness


Você provavelmente já usou o ChatGPT ou uma API de LLM (Large Language Model) e pensou: "legal, mas como isso vira um produto real?"

O problema aparece quando você tenta construir algo sério:
- O modelo "esquece" o que fez três passos atrás
- Chamadas de ferramentas falham silenciosamente
- A "janela de contexto" enche com lixo

**A conclusão-chave do artigo:** o problema não é o modelo. É tudo ao redor do modelo.

A prova disso foi o que o LangChain fez: usou **exatamente o mesmo modelo, com os mesmos pesos** e apenas mudou a infraestrutura ao redor. Resultado: pulou de fora do top 30 para a posição 5 num benchmark importante. Um sistema de infraestrutura otimizada por IA chegou a 76.4% de taxa de sucesso, superando sistemas projetados à mão.

Essa infraestrutura tem um nome: **Agent Harness**.

---

## O que é um Agent Harness?

> "Se você não é o modelo, você é o harness." — Vivek Trivedy, LangChain

**Analogia para engenheiro de software:** pense em como funciona uma aplicação web moderna.

```
Requisição HTTP
      ↓
  [Nginx/Load Balancer]  → autenticação, rate limiting
      ↓
  [Framework Web]        → roteamento, middleware, validação
      ↓
  [Sua lógica de negócio]← o código que você realmente escreveu
      ↓
  [ORM / Driver de DB]   → persistência, conexão, pool
      ↓
   Banco de dados
```

Agora compare com um agente de IA:

```
Mensagem do usuário
      ↓
  [Guardrails]           → filtros de segurança, validação
      ↓
  [Orchestration Loop]   → o "event loop" do agente
      ↓
  [O Modelo (LLM)]       ← o "motor" que você não controla
      ↓
  [Tool Executor]        → executa ações no mundo real
      ↓
  [Memory & State]       → persistência entre turnos
```

**O harness é tudo exceto o modelo.** É o Express.js do mundo de agentes. É o Spring Boot. É o Django. O LLM é apenas o "banco de dados" onde você consulta raciocínio.

### A Analogia do Sistema Operacional

O artigo traz uma analogia ainda mais precisa, de Beren Millidge:

| Sistema Operacional | Agent Harness |
|---------------------|---------------|
| CPU | O modelo (LLM) |
| RAM | Janela de contexto (rápida, limitada) |
| Disco | Banco de dados externo (grande, lento) |
| Device Drivers | Integrações com ferramentas |
| Sistema Operacional | O harness |

Um LLM sem harness é como um CPU sem sistema operacional: poderoso, mas inútil na prática.

---

## Os Três Níveis de Engenharia

Existe uma hierarquia clara de onde o trabalho acontece:

```
┌─────────────────────────────────────────────────┐
│           HARNESS ENGINEERING                   │
│  (orquestração, estado, erros, segurança)        │
│                                                 │
│   ┌─────────────────────────────────────────┐   │
│   │        CONTEXT ENGINEERING              │   │
│   │   (o que o modelo vê e quando vê)       │   │
│   │                                         │   │
│   │   ┌─────────────────────────────────┐   │   │
│   │   │      PROMPT ENGINEERING         │   │   │
│   │   │  (como escrever as instruções)  │   │   │
│   │   └─────────────────────────────────┘   │   │
│   └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

A maioria dos tutoriais ensina apenas **prompt engineering** — como escrever bons prompts. Isso é o nível mais interno e mais básico. O artigo fala do nível mais externo: **harness engineering**.

---

## Os 12 Componentes de um Harness em Produção

Vou explicar cada um com analogias de software que você já conhece.

---

### 1. O Loop de Orquestração (Orchestration Loop)

**Analogia:** é o `event loop` do Node.js, ou o `while True` de um servidor de sockets.

É o coração do agente. Implementa o ciclo **TAO** (Thought-Action-Observation), também chamado de **ReAct loop**:

```python
while not done:
    prompt = montar_prompt(historico, ferramentas, memoria)
    resposta = chamar_llm(prompt)
    
    if resposta.tem_chamada_de_ferramenta():
        resultado = executar_ferramenta(resposta.ferramenta)
        historico.append(resultado)
    else:
        # Resposta final — sem chamadas de ferramenta
        done = True
        return resposta.texto
```

Mecanicamente é simples — um `while loop`. A complexidade está em **tudo que esse loop gerencia**, não no loop em si.

> A Anthropic descreve o runtime como um "dumb loop" (loop burro): toda a inteligência vive no modelo. O harness apenas gerencia os turnos.

---

### 2. Ferramentas (Tools)

**Analogia:** são como endpoints de uma API REST, mas chamados pelo modelo.

Cada ferramenta é definida como um schema (JSON Schema, semelhante ao que você usa para validar payloads de API):

```json
{
  "name": "buscar_arquivo",
  "description": "Lê o conteúdo de um arquivo no sistema de arquivos",
  "parameters": {
    "type": "object",
    "properties": {
      "caminho": {
        "type": "string",
        "description": "Caminho absoluto do arquivo"
      }
    },
    "required": ["caminho"]
  }
}
```

Esse schema vai para o contexto do LLM, e o modelo "sabe" o que pode chamar. O harness então:
1. Valida os argumentos
2. Executa em ambiente sandboxed
3. Captura o resultado
4. Formata de volta como mensagem para o modelo

O Claude Code tem ferramentas em 6 categorias: operações de arquivo, busca, execução, acesso web, inteligência de código, e spawn de sub-agentes.

---

### 3. Memória (Memory)

**Analogia:** é a combinação de sessão HTTP (curto prazo) + banco de dados (longo prazo).

Existem múltiplos níveis de memória:

```
┌──────────────────────────────────────────────┐
│  Memória de Curto Prazo                       │
│  (histórico da conversa na sessão atual)      │
│  → Como variáveis em memória RAM              │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│  Memória de Longo Prazo                       │
│  (persiste entre sessões)                     │
│  → Como um banco de dados                    │
│                                              │
│  Anthropic: arquivos CLAUDE.md e MEMORY.md   │
│  LangGraph: JSON Stores por namespace        │
│  OpenAI: SQLite ou Redis                     │
└──────────────────────────────────────────────┘
```

O Claude Code usa uma hierarquia de 3 níveis:
1. **Índice leve** (~150 chars por entrada, sempre carregado) → como um cache em memória
2. **Arquivos de tópico detalhados** (carregados sob demanda) → como lazy loading
3. **Transcrições brutas** (acessadas via busca apenas) → como consultar logs

**Princípio crítico:** o agente trata sua própria memória como uma "dica" e verifica o estado real antes de agir. Isso previne alucinações baseadas em memória desatualizada.

---

### 4. Gerenciamento de Contexto (Context Management)

**Analogia:** é como gerenciamento de memória e garbage collection, mas para tokens.

Este é onde a maioria dos agentes falha silenciosamente.

**O problema — Context Rot:** performance do modelo degrada 30%+ quando conteúdo importante cai no meio da janela de contexto (o modelo "esquece" o que está no meio). Pesquisa da Stanford chamou isso de "Lost in the Middle" (Perdido no Meio).

Estratégias de produção:

| Estratégia | Analogia de Software | Como funciona |
|------------|---------------------|---------------|
| **Compaction** | Compressão de logs | Resume o histórico quando se aproxima do limite |
| **Observation Masking** | Paginação de resultados | Esconde outputs antigos de ferramentas, mantém só as chamadas |
| **Just-in-Time Retrieval** | Lazy loading | Mantém identificadores leves, carrega dados dinamicamente |
| **Sub-agent Delegation** | Microserviço com resposta resumida | Subagente explora extensamente, retorna apenas 1-2k tokens resumidos |

> A meta do Claude Code: encontrar o menor conjunto possível de tokens de alto sinal que maximize a probabilidade do resultado desejado.

---

### 5. Construção de Prompt (Prompt Construction)

**Analogia:** é como montar os headers de uma requisição HTTP — hierárquico e ordenado.

O que o modelo vê em cada turno é uma pilha hierárquica:

```
┌─────────────────────────────┐ ← Maior prioridade
│  System Prompt              │   (instruções do sistema)
├─────────────────────────────┤
│  Tool Definitions           │   (schemas das ferramentas)
├─────────────────────────────┤
│  Memory Files               │   (contexto de longo prazo)
├─────────────────────────────┤
│  Conversation History       │   (histórico da conversa)
├─────────────────────────────┤
│  Current User Message       │   (mensagem atual)
└─────────────────────────────┘ ← Menor prioridade
```

**Detalhe crítico (Lost in the Middle):** contexto importante deve ir no **começo** ou no **fim** do prompt, nunca no meio.

---

### 6. Parsing de Output (Output Parsing)

**Analogia:** é como deserializar uma resposta de API.

Harnesses modernos usam **native tool calling** — o modelo retorna objetos `tool_calls` estruturados em vez de texto livre que precisaria ser parseado com regex.

A lógica é simples:

```python
resposta = llm.completar(prompt)

if resposta.tool_calls:
    # Executar ferramentas e voltar ao loop
    for chamada in resposta.tool_calls:
        resultado = executar(chamada)
        historico.append(resultado)
else:
    # Sem chamadas = resposta final
    return resposta.texto
```

Para outputs estruturados, tanto OpenAI quanto LangChain suportam respostas constrangidas por schema via modelos Pydantic.

---

### 7. Gerenciamento de Estado (State Management)

**Analogia:** é como gerenciar estado em Redux ou em uma máquina de estados.

O LangGraph modela estado como dicionários tipados fluindo por nós de um grafo, com checkpointing em limites de "super-step" — permitindo retomar após interrupções e debugging "no tempo" (time-travel debugging).

O Claude Code usa uma abordagem diferente: **commits git como checkpoints** e arquivos de progresso como scratchpads estruturados. O filesystem provê continuidade entre janelas de contexto.

Estratégias disponíveis no OpenAI:
- Memória da aplicação (você gerencia)
- Sessões do SDK (gerenciado pelo SDK)
- Conversations API (server-side)
- `previous_response_id` chaining (leve)

---

### 8. Tratamento de Erros (Error Handling)

**Analogia:** é como circuit breaker pattern, mas para chamadas de LLM e ferramentas.

**Por que isso importa tanto:**

```
Processo de 10 etapas com 99% de sucesso por etapa:
0.99^10 = 90.4% de sucesso end-to-end

Processo de 20 etapas com 99% de sucesso por etapa:
0.99^20 = 81.8% de sucesso end-to-end

Processo de 50 etapas com 95% de sucesso por etapa:
0.95^50 = 7.7% de sucesso end-to-end ← DESASTRE
```

Erros se compõem rapidamente.

O LangGraph classifica 4 tipos de erros:

| Tipo | O que é | O que fazer |
|------|---------|-------------|
| **Transiente** | Timeout de rede, rate limit | Retry com backoff exponencial |
| **Recuperável pelo LLM** | Argumento inválido para ferramenta | Retornar como `ToolMessage` de erro — o modelo se corrige |
| **Requer usuário** | Precisa de credencial, permissão | Interromper e pedir ao humano |
| **Inesperado** | Bug no código, estado corrompido | Bubble up para debugging |

A Anthropic captura falhas dentro dos handlers de ferramenta e retorna como resultados de erro para **manter o loop rodando**.

O Stripe limita tentativas de retry a no máximo 2.

---

### 9. Guardrails e Segurança

**Analogia:** é como middleware de autenticação/autorização em 3 níveis.

O OpenAI implementa 3 níveis:

```
Entrada do usuário → [Input Guardrails]   → validação de entrada
Loop de execução  → [Tool Guardrails]    → validação de cada ferramenta
Saída final       → [Output Guardrails]  → validação da resposta
```

Um mecanismo de **"tripwire"** para o agente imediatamente quando acionado.

A Anthropic separa arquiteturalmente **permissão** de **raciocínio**:
- O modelo decide **o que tentar**
- O sistema de ferramentas decide **o que é permitido**

O Claude Code controla ~40 capacidades de ferramentas independentemente, com 3 estágios:
1. Estabelecimento de confiança ao carregar o projeto
2. Verificação de permissão antes de cada chamada de ferramenta
3. Confirmação explícita do usuário para operações de alto risco

---

### 10. Loops de Verificação (Verification Loops)

**Analogia:** é como TDD + CI/CD, mas dentro do próprio agente.

> Boris Cherny, criador do Claude Code: "dar ao modelo uma forma de verificar seu trabalho melhora a qualidade em 2 a 3x."

3 abordagens:

| Abordagem | Como funciona | Analogia |
|-----------|--------------|----------|
| **Baseada em regras** | Testes, linters, type checkers | CI/CD pipeline |
| **Visual** | Screenshots via Playwright para tarefas de UI | QA manual automatizado |
| **LLM-as-Judge** | Um subagente avalia o output | Code review automatizado |

A distinção do Thoughtworks:
- **Guides** (feedforward): orienta antes de agir — como lint antes de commitar
- **Sensors** (feedback): observa após agir — como alertas de monitoramento

---

### 11. Orquestração de Sub-agentes

**Analogia:** é como microsserviços ou worker threads.

O Claude Code suporta 3 modelos de execução:

| Modelo | Como funciona | Analogia |
|--------|--------------|----------|
| **Fork** | Cópia byte-idêntica do contexto do pai | `fork()` em Unix |
| **Teammate** | Terminal separado com comunicação por arquivo | Processo separado com IPC |
| **Worktree** | Própria branch git isolada | Container isolado |

O OpenAI suporta:
- **Agents-as-tools**: especialista lida com subtarefa delimitada
- **Handoffs**: especialista assume controle total

---

### 12. (O Prompt em Si — a base de tudo)

O sistema prompt é o "contrato" entre você e o modelo. Ele define:
- Qual papel o agente tem
- Quais ferramentas existem e como usá-las
- Restrições e guardrails
- Formato esperado de resposta

---

## O Loop em Movimento: Passo a Passo

Agora que você conhece os componentes, veja como eles colaboram num ciclo completo:

```
┌─────────────────────────────────────────────────────────┐
│ PASSO 1: Montagem do Prompt                             │
│ system_prompt + tool_schemas + memory + historico +     │
│ mensagem_atual → contexto completo                      │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ PASSO 2: Inferência do LLM                              │
│ O modelo processa o contexto e gera tokens:             │
│ texto, chamadas de ferramentas, ou ambos                │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ PASSO 3: Classificação do Output                        │
│ Sem tool calls → FIM (retornar resposta)                │
│ Com tool calls → continuar para execução                │
│ Handoff → trocar agente e reiniciar                     │
└────────────────────────┬────────────────────────────────┘
                         ↓ (se tool calls)
┌─────────────────────────────────────────────────────────┐
│ PASSO 4: Execução de Ferramentas                        │
│ Validar argumentos → checar permissões →                │
│ executar em sandbox → capturar resultado                │
│ (read-only: concorrente | mutante: serial)              │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ PASSO 5: Empacotamento de Resultados                    │
│ Formatar resultados como mensagens para o LLM           │
│ Erros viram ToolMessages para auto-correção             │
└────────────────────────┬────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ PASSO 6: Atualização de Contexto                        │
│ Resultados adicionados ao histórico                     │
│ Se próximo do limite → compaction                       │
└────────────────────────┬────────────────────────────────┘
                         ↓
                    VOLTA AO PASSO 1
```

### Condições de Terminação

O loop para quando:
- Modelo gera resposta sem tool calls
- Limite máximo de turnos excedido
- Budget de tokens esgotado
- Tripwire de guardrail disparado
- Usuário interrompe
- Refusa de segurança retornada

Uma pergunta simples: 1-2 turnos. Uma refatoração complexa: dezenas de tool calls ao longo de muitos turnos.

---

## Como os Frameworks Reais Implementam

### Anthropic Claude Agent SDK

```python
# Loop simples — toda inteligência no modelo
async for message in client.messages.stream(...):
    process(message)
```

O runtime é o "dumb loop". O Claude Code usa ciclo **Gather-Act-Verify**:
1. **Gather**: busca arquivos, lê código
2. **Act**: edita arquivos, roda comandos
3. **Verify**: roda testes, verifica output
4. Repete

### OpenAI Agents SDK

```python
# Code-first: lógica em Python nativo, não DSLs
result = await Runner.run(agent, input="...")
```

### LangGraph

Modela o harness como um **grafo de estado explícito**:

```
[llm_call] → (tem tool calls?) → Sim → [tool_node] → volta para [llm_call]
                                   Não → [END]
```

### CrewAI

Arquitetura **role-based** multi-agente:
- `Agent`: o harness ao redor do LLM (papel, objetivo, ferramentas)
- `Task`: a unidade de trabalho
- `Crew`: a coleção de agentes

---

## A Metáfora do Andaime

> "Andaime de construção é infraestrutura temporária que permite a trabalhadores construir uma estrutura que não alcançariam de outra forma. Ele não faz a construção. Mas sem ele, os trabalhadores não chegam aos andares superiores."

**A ideia-chave:** conforme os modelos melhoram, a complexidade do harness deve diminuir.

O Manus foi reconstruído 5 vezes em 6 meses, cada reescrita removendo complexidade. Definições complexas de ferramentas viraram execução de shell genérica. "Agentes de gerenciamento" viraram handoffs estruturados simples.

**O princípio de co-evolução:** modelos são agora treinados com harnesses específicos no loop. O modelo do Claude Code aprendeu a usar o harness específico com que foi treinado. Mudar implementações de ferramentas pode degradar performance por causa deste acoplamento.

**O teste de future-proofing:** se a performance escala com modelos mais poderosos sem adicionar complexidade ao harness, o design é sólido.

---

## As 7 Decisões que Definem Todo Harness

Ao construir seu próprio harness, você vai enfrentar estas escolhas:

### 1. Agente único vs. Multi-agente

> Anthropic e OpenAI dizem: **maximize um único agente primeiro.**

Multi-agente adiciona overhead (LLM calls extras para roteamento, perda de contexto em handoffs). Divida apenas quando:
- Sobrecarga de ferramentas excede ~10 ferramentas sobrepostas
- Domínios de tarefa claramente separados existem

### 2. ReAct vs. Plan-and-Execute

| | ReAct | Plan-and-Execute |
|--|-------|-----------------|
| **Como funciona** | Intercala raciocínio e ação a cada passo | Separa planejamento de execução |
| **Vantagem** | Flexível, adapta-se ao resultado de cada passo | 3.6x mais rápido (LLMCompiler) |
| **Desvantagem** | Custo maior por passo | Menos adaptável |

### 3. Estratégia de janela de contexto

5 abordagens de produção:
- Limpeza por tempo
- Sumarização de conversa
- Mascaramento de observação
- Tomada de notas estruturada
- Delegação para sub-agentes

Pesquisa ACON: redução de 26-54% de tokens preservando 95%+ de precisão, priorizando traces de raciocínio sobre outputs brutos de ferramentas.

### 4. Design do Loop de Verificação

- **Verificação computacional** (testes, linters): ground truth determinístico
- **Verificação inferencial** (LLM-as-judge): captura problemas semânticos, mas adiciona latência

### 5. Arquitetura de permissão e segurança

| | Permissiva | Restritiva |
|--|-----------|-----------|
| **Velocidade** | Rápida | Lenta |
| **Risco** | Alto | Baixo |
| **Uso** | Ambiente controlado | Produção com dados sensíveis |

### 6. Estratégia de escopo de ferramentas

> Vercel removeu 80% das ferramentas do v0 e obteve resultados melhores.

Mais ferramentas = pior performance. Exponha o conjunto mínimo necessário para o passo atual. Claude Code alcança 95% de redução de contexto via lazy loading.

### 7. Espessura do harness

| | Harness fino | Harness espesso |
|--|------------|----------------|
| **Lógica em** | No modelo | No código do harness |
| **Defensores** | Anthropic | Frameworks baseados em grafos |
| **Tendência** | Anthropic regularmente deleta etapas de planejamento do Claude Code conforme novos modelos internalizam essa capacidade | Mais controle explícito |

---

## A Conclusão Principal

> "Dois produtos usando modelos idênticos podem ter performance completamente diferente baseada apenas no design do harness."

A evidência do TerminalBench é clara: mudar apenas o harness moveu agentes em 20+ posições no ranking.

O harness **não é um problema resolvido** ou uma camada commodity. É onde a engenharia difícil vive:
- Gerenciar contexto como recurso escasso
- Projetar loops de verificação que capturam falhas antes de se comporem
- Construir sistemas de memória que fornecem continuidade sem alucinação
- Fazer apostas arquitetônicas sobre quanto scaffolding construir vs. quanto deixar para o modelo

O campo está se movendo em direção a harnesses mais finos conforme os modelos melhoram. Mas o harness em si não vai desaparecer. Mesmo o modelo mais capaz precisa de algo para gerenciar sua janela de contexto, executar suas chamadas de ferramentas, persistir seu estado e verificar seu trabalho.

**Da próxima vez que seu agente falhar, não culpe o modelo. Olhe para o harness.**

---

## Glossário Rápido

| Termo | Tradução/Significado |
|-------|---------------------|
| **Agent Harness** | A infraestrutura completa ao redor do LLM |
| **LLM** | Large Language Model (GPT-4, Claude, Gemini...) |
| **Orchestration Loop** | O loop principal que gerencia turnos do agente |
| **ReAct Loop** | Thought-Action-Observation: o padrão de raciocínio-ação do agente |
| **Context Window** | Limite de tokens que o modelo consegue "ver" de uma vez |
| **Context Rot** | Degradação de performance quando informação cai no meio do contexto |
| **Compaction** | Compressão/sumarização do histórico para liberar espaço no contexto |
| **Guardrails** | Sistemas de segurança que controlam o que o agente pode fazer |
| **Tool Call** | Quando o modelo decide usar uma ferramenta |
| **Handoff** | Quando um agente passa o controle para outro agente especialista |
| **Subagent** | Agente filho criado pelo agente principal para tarefas paralelas |
| **Checkpoint** | Snapshot do estado para permitir retomada após falha |
| **Plan-and-Execute** | Padrão onde planejamento e execução são fases separadas |
| **LLM-as-Judge** | Usar um LLM para avaliar o output de outro LLM |
| **Tripwire** | Mecanismo que para o agente imediatamente ao ser acionado |
