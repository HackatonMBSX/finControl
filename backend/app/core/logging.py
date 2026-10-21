"""Configuração dos logs em formato JSON.

Este arquivo faz cada linha de log sair como um objeto JSON na saída padrão, com data, nível, origem e mensagem.
Quando presentes, campos extras como request_id, método, caminho, status, duração, família e contagens do backup
também entram no JSON; campos extras fora dessa lista são ignorados.
Isso facilita filtrar e buscar os logs em ferramentas de monitoramento.
Quem usa: main.py, ao criar a aplicação.
"""

import json
import logging
import sys
from datetime import UTC, datetime


class JsonFormatter(logging.Formatter):
    """Formatador que transforma cada registro de log em uma linha JSON."""

    EXTRA_KEYS = ("request_id", "method", "path", "status", "duration_ms", "user_id", "family_id", "contagens")

    def format(self, record: logging.LogRecord) -> str:
        """Converte o registro em JSON, copiando os campos extras conhecidos e o erro, se houver."""
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in self.EXTRA_KEYS:
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    """Troca os handlers do logger raiz por um único handler JSON no stdout e ajusta o nível."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level.upper())
