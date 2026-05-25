"""
HELLO WORLD — Agent Harness
============================
Ponto de entrada do agente. Demonstra todos os 12 componentes
descritos no artigo "The Anatomy of an Agent Harness".

Como rodar:
    export ANTHROPIC_API_KEY="sua-chave-aqui"
    python main.py

O agente vai rodar em modo interativo. Digite 'sair' para encerrar.
"""

import os
import anthropic
from memory import Memoria
from harness import rodar_agente

BANNER = """
╔══════════════════════════════════════════════════════════╗
║          HELLO WORLD — Agent Harness                     ║
║                                                          ║
║  Componentes ativos:                                     ║
║  [1] Orchestration Loop    [7] State Management          ║
║  [2] Tools (4 ferramentas) [8] Error Handling            ║
║  [3] Memory (2 níveis)     [9] Guardrails                ║
║  [4] Context Management   [10] Verification Loops        ║
║  [5] Prompt Construction  [11] (single-agent)            ║
║  [6] Output Parsing       [12] System Prompt             ║
║                                                          ║
║  Ferramentas: calcular | salvar_nota | ler_notas |       ║
║               hora_atual                                 ║
╚══════════════════════════════════════════════════════════╝

Exemplos de perguntas para testar:
  → "Quanto é raiz quadrada de 144 mais 50 dividido por 2?"
  → "Salve uma nota: meu modelo favorito é Claude Haiku"
  → "Que horas são agora?"
  → "Mostre minhas notas salvas"
  → "Qual a data de hoje e quanto é 365 dividido por 7?"

"""


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Erro: defina a variável de ambiente ANTHROPIC_API_KEY")
        print("  export ANTHROPIC_API_KEY='sua-chave-aqui'")
        return

    client = anthropic.Anthropic(api_key=api_key)

    # COMPONENTE #3: Inicializar memória (curto + longo prazo)
    memoria = Memoria()

    print(BANNER)
    print(f"Estado inicial: {memoria.resumo()}\n")

    # Loop de interação com o usuário
    while True:
        try:
            entrada = input("Você: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSaindo...")
            break

        if not entrada:
            continue

        if entrada.lower() in ("sair", "exit", "quit"):
            print("Até logo!")
            break

        print()
        # COMPONENTE #1: Rodar o loop de orquestração
        resposta = rodar_agente(entrada, memoria, client)
        print(f"Agente: {resposta}")
        print(f"\n[Memória] {memoria.resumo()}\n")
        print("-" * 60)


if __name__ == "__main__":
    main()
