"""
O HARNESS COMPLETO
==================
Este arquivo implementa o coração do agente:
o loop de orquestração e todos os componentes ao redor.

Componentes implementados aqui:
  #1  - Orchestration Loop (o while loop principal)
  #5  - Prompt Construction (montar_prompt)
  #6  - Output Parsing (classificar_resposta)
  #7  - State Management (via Memoria)
  #8  - Error Handling (try/except em cada passo)
  #9  - Guardrails (guardrail_simples)
  #10 - Verification Loops (verificar_resultado)
"""

import anthropic
from memory import Memoria
from tools import TOOL_SCHEMAS, executar_ferramenta

# ── Constantes ───────────────────────────────────────────────────────────────

MODELO = "claude-haiku-4-5-20251001"  # Haiku: mais rápido e barato para demos
MAX_TURNOS = 10                         # Componente #8: evita loops infinitos

# ── COMPONENTE #5: System Prompt ──────────────────────────────────────────────
#
# Este é o "contrato" com o modelo. Define:
# - Qual papel o agente tem
# - Quando usar ferramentas
# - Formato esperado de resposta

SYSTEM_PROMPT = """Você é um assistente útil com acesso a ferramentas.

Ferramentas disponíveis:
- calcular: para expressões matemáticas
- salvar_nota: para guardar informações importantes
- ler_notas: para consultar notas salvas
- hora_atual: para saber a data e hora

Seja direto e conciso. Use ferramentas quando necessário para dar respostas precisas.
Responda sempre em português."""


# ── COMPONENTE #9: Guardrails ─────────────────────────────────────────────────

TERMOS_PROIBIDOS = ["deletar", "formatar disco", "sudo rm"]


def guardrail_entrada(mensagem: str) -> str | None:
    """
    Verifica a entrada do usuário antes de processar.
    Retorna uma mensagem de erro se bloqueada, None se ok.

    Analogia: middleware de autenticação/autorização.
    """
    mensagem_lower = mensagem.lower()
    for termo in TERMOS_PROIBIDOS:
        if termo in mensagem_lower:
            return f"Solicitação bloqueada: termo proibido detectado ('{termo}')."
    return None


def guardrail_saida(resposta: str) -> str | None:
    """
    Verifica a saída do modelo antes de entregar ao usuário.
    Em produção: detectar PII, conteúdo sensível, etc.
    """
    if len(resposta) > 5000:
        return "Resposta muito longa gerada. Considere reformular a pergunta."
    return None


# ── COMPONENTE #10: Verificação de Resultado ──────────────────────────────────

def verificar_resultado_ferramenta(nome_ferramenta: str, resultado: str) -> str:
    """
    Verificação simples: detecta se uma ferramenta retornou erro.

    Em produção real: rodar testes, linters, ou LLM-as-judge.
    Aqui: checar prefixo de erro (suficiente para demo).
    """
    if resultado.startswith("Erro"):
        print(f"  [Verificação] Ferramenta '{nome_ferramenta}' retornou erro: {resultado[:60]}...")
    return resultado  # Retorna de qualquer jeito — o modelo decide o que fazer


# ── COMPONENTE #6: Output Parsing ────────────────────────────────────────────

def classificar_resposta(mensagem) -> str:
    """
    Classifica o output do modelo em 3 categorias:
    - 'tool_use': modelo quer usar ferramentas → continuar loop
    - 'end_turn': modelo terminou → retornar ao usuário
    - 'error': algo inesperado

    Harnesses modernos usam native tool calling (não regex em texto livre).
    """
    if mensagem.stop_reason == "tool_use":
        return "tool_use"
    elif mensagem.stop_reason in ("end_turn", "stop_sequence", "max_tokens"):
        return "end_turn"
    else:
        return "error"


# ── COMPONENTE #1: Orchestration Loop ────────────────────────────────────────

def rodar_agente(mensagem_usuario: str, memoria: Memoria, client: anthropic.Anthropic) -> str:
    """
    O coração do harness: o loop de orquestração.

    Implementa o ciclo TAO (Thought-Action-Observation):
    1. Monta prompt
    2. Chama LLM
    3. Classifica resposta
    4. Executa ferramentas (se houver)
    5. Adiciona resultado ao histórico
    6. Repete

    Analogia: event loop do Node.js, mas para LLM.
    """

    # ── COMPONENTE #9: Guardrail de entrada ──────────────────────────────────
    erro_guardrail = guardrail_entrada(mensagem_usuario)
    if erro_guardrail:
        return erro_guardrail

    # ── COMPONENTE #3: Adicionar mensagem ao histórico (memória de curto prazo)
    memoria.adicionar_mensagem("user", mensagem_usuario)

    # ── COMPONENTE #4: Compactar contexto se necessário ──────────────────────
    memoria.compactar_se_necessario(limite_mensagens=20)

    turno = 0

    # ── COMPONENTE #1: O Loop Principal ──────────────────────────────────────
    while turno < MAX_TURNOS:
        turno += 1
        print(f"  [Loop] Turno {turno}/{MAX_TURNOS}")

        # ── COMPONENTE #5: Construção do Prompt ──────────────────────────────
        # Hierarquia: system_prompt > tool_schemas > historico
        try:
            resposta = client.messages.create(
                model=MODELO,
                max_tokens=1024,
                system=SYSTEM_PROMPT,           # Nível 1: system
                tools=TOOL_SCHEMAS,              # Nível 2: ferramentas disponíveis
                messages=memoria.historico,      # Nível 3: histórico da conversa
            )
        except anthropic.APIError as e:
            # ── COMPONENTE #8: Tratamento de erros de API (transiente) ───────
            return f"Erro de API: {e}. Tente novamente."

        # ── COMPONENTE #6: Classificação do output ───────────────────────────
        tipo_resposta = classificar_resposta(resposta)

        if tipo_resposta == "end_turn":
            # Modelo terminou — extrair texto e retornar
            texto_final = next(
                (bloco.text for bloco in resposta.content if hasattr(bloco, "text")),
                "Sem resposta."
            )

            # ── COMPONENTE #9: Guardrail de saída ────────────────────────────
            erro_saida = guardrail_saida(texto_final)
            if erro_saida:
                return erro_saida

            # ── COMPONENTE #7: Persistir estado ──────────────────────────────
            memoria.adicionar_mensagem("assistant", resposta.content)
            memoria.salvar_notas()

            return texto_final

        elif tipo_resposta == "tool_use":
            # Modelo quer usar ferramentas
            # Adicionar resposta do modelo ao histórico
            memoria.adicionar_mensagem("assistant", resposta.content)

            # ── COMPONENTE #2: Executar ferramentas ───────────────────────────
            resultados_ferramentas = []

            for bloco in resposta.content:
                if bloco.type != "tool_use":
                    continue

                nome = bloco.name
                argumentos = bloco.input
                print(f"  [Ferramenta] Chamando '{nome}' com {argumentos}")

                # Execução com tratamento de erro integrado
                resultado = executar_ferramenta(nome, argumentos, memoria.notas)

                # ── COMPONENTE #10: Verificar resultado ───────────────────────
                resultado = verificar_resultado_ferramenta(nome, resultado)

                resultados_ferramentas.append({
                    "type": "tool_result",
                    "tool_use_id": bloco.id,
                    "content": resultado,
                })

            # ── COMPONENTE #5: Adicionar resultados ao histórico e repetir ───
            memoria.adicionar_mensagem("user", resultados_ferramentas)

        else:
            # ── COMPONENTE #8: Resposta inesperada ───────────────────────────
            return f"Resposta inesperada do modelo (stop_reason={resposta.stop_reason})."

    # ── COMPONENTE #8: Limite de turnos excedido ─────────────────────────────
    return f"Limite de {MAX_TURNOS} turnos atingido sem resposta final."
