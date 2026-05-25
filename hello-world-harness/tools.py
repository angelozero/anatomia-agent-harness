"""
COMPONENTE 2 — FERRAMENTAS (Tools)
===================================
Analogia: endpoints de uma API que o modelo pode "chamar".

Cada ferramenta tem:
- Um nome
- Uma descrição (o modelo usa isso para decidir quando chamar)
- Parâmetros tipados (schema JSON)
- Uma função Python de implementação
"""

import json
import math
from datetime import datetime


# ── Definições de schema (o que o modelo "vê") ──────────────────────────────

TOOL_SCHEMAS = [
    {
        "name": "calcular",
        "description": (
            "Avalia uma expressão matemática simples. "
            "Use para somar, subtrair, multiplicar, dividir ou calcular raiz quadrada."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "expressao": {
                    "type": "string",
                    "description": "Expressão matemática em Python válida. Ex: '2 + 2', 'math.sqrt(16)'",
                }
            },
            "required": ["expressao"],
        },
    },
    {
        "name": "salvar_nota",
        "description": "Salva uma nota de texto para lembrar depois. Use para guardar informações importantes.",
        "input_schema": {
            "type": "object",
            "properties": {
                "titulo": {"type": "string", "description": "Título curto da nota"},
                "conteudo": {"type": "string", "description": "Conteúdo da nota"},
            },
            "required": ["titulo", "conteudo"],
        },
    },
    {
        "name": "ler_notas",
        "description": "Lista todas as notas salvas anteriormente.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "hora_atual",
        "description": "Retorna a data e hora atual do sistema.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ── Implementações (o que realmente executa) ─────────────────────────────────

def calcular(expressao: str, notas: dict) -> str:
    # Usa um namespace seguro — sem acesso a __builtins__ arbitrários
    namespace_seguro = {"math": math, "__builtins__": {}}
    try:
        resultado = eval(expressao, namespace_seguro)  # noqa: S307
        return f"Resultado de `{expressao}` = {resultado}"
    except Exception as e:
        return f"Erro ao calcular `{expressao}`: {e}"


def salvar_nota(titulo: str, conteudo: str, notas: dict) -> str:
    notas[titulo] = conteudo
    return f"Nota '{titulo}' salva com sucesso."


def ler_notas(notas: dict) -> str:
    if not notas:
        return "Nenhuma nota salva ainda."
    linhas = [f"### {titulo}\n{conteudo}" for titulo, conteudo in notas.items()]
    return "Notas salvas:\n\n" + "\n\n".join(linhas)


def hora_atual(notas: dict) -> str:
    agora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    return f"Data e hora atual: {agora}"


# ── Dispatcher: mapeia nome → função ─────────────────────────────────────────

TOOL_FUNCTIONS = {
    "calcular": calcular,
    "salvar_nota": salvar_nota,
    "ler_notas": ler_notas,
    "hora_atual": hora_atual,
}


def executar_ferramenta(nome: str, argumentos: dict, notas: dict) -> str:
    """
    COMPONENTE 4 (parte) — Execução em sandbox + captura de resultado.

    Valida que a ferramenta existe, executa, e captura qualquer erro
    para retornar como resultado (não como exceção que quebraria o loop).
    """
    if nome not in TOOL_FUNCTIONS:
        # Erro retornado como string — o modelo pode se corrigir
        return f"Ferramenta desconhecida: '{nome}'. Ferramentas disponíveis: {list(TOOL_FUNCTIONS.keys())}"

    try:
        funcao = TOOL_FUNCTIONS[nome]
        return funcao(**argumentos, notas=notas)
    except TypeError as e:
        # Argumentos errados — o modelo pode se corrigir
        return f"Erro nos argumentos da ferramenta '{nome}': {e}"
    except Exception as e:
        # Erro inesperado — ainda retornamos como string para manter o loop
        return f"Erro inesperado em '{nome}': {e}"
