"""
COMPONENTE 3 — MEMÓRIA (Memory)
================================
Analogia: combinação de sessão HTTP (curto prazo) + arquivo JSON (longo prazo).

Dois níveis de memória:
- Curto prazo: histórico da conversa (messages[]) — persiste na sessão
- Longo prazo: notas salvas em arquivo JSON — persiste entre sessões
"""

import json
from pathlib import Path

MEMORIA_PATH = Path(__file__).parent / "memoria.json"


class Memoria:
    def __init__(self):
        # Curto prazo: histórico de mensagens desta sessão
        # (este é o "context window" — o que o modelo "vê")
        self.historico: list[dict] = []

        # Longo prazo: notas persistentes em disco
        # (equivalente a um banco de dados simples)
        self.notas: dict[str, str] = self._carregar_notas()

    def adicionar_mensagem(self, role: str, content):
        """Adiciona uma mensagem ao histórico de curto prazo."""
        self.historico.append({"role": role, "content": content})

    def _carregar_notas(self) -> dict:
        """Carrega notas do disco (memória de longo prazo)."""
        if MEMORIA_PATH.exists():
            try:
                return json.loads(MEMORIA_PATH.read_text())
            except json.JSONDecodeError:
                return {}
        return {}

    def salvar_notas(self):
        """Persiste notas no disco."""
        MEMORIA_PATH.write_text(json.dumps(self.notas, indent=2, ensure_ascii=False))

    def compactar_se_necessario(self, limite_mensagens: int = 20):
        """
        COMPONENTE 4 — Gerenciamento de Contexto (Context Management).

        Estratégia: quando o histórico fica grande, remove as mensagens
        mais antigas do meio (mantém system + últimas N mensagens).

        Em produção real: sumarizar com LLM ao invés de truncar.
        """
        if len(self.historico) > limite_mensagens:
            print(f"  [Contexto] Compactando: {len(self.historico)} → {limite_mensagens} mensagens")
            # Mantém as últimas N mensagens
            self.historico = self.historico[-limite_mensagens:]

    def resumo(self) -> str:
        """Retorna um resumo do estado atual da memória."""
        return (
            f"Histórico: {len(self.historico)} mensagens | "
            f"Notas salvas: {len(self.notas)}"
        )
