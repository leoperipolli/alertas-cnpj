"""Para onde o post vai.

Esta é a costura que importa. Hoje o post vai para o seu Telegram e VOCÊ publica no X
— porque em fev/2026 o X acabou com o free tier da API e virou pay-per-use, e não faz
sentido pôr cartão antes de saber se o formato engaja.

No dia em que fizer sentido, `XPublisher` deixa de ser stub. É um arquivo, não uma
refatoração — que é justamente o motivo de existir uma interface aqui com um publisher só.
"""

import os
from typing import Protocol

import requests

from .cortes import Post


class Publisher(Protocol):
    def publish(self, post: Post) -> str: ...


class TelegramPublisher:
    """Manda o post pronto para o seu celular. Você copia, cola no X, e acabou."""

    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.environ["TELEGRAM_BOT_TOKEN"]
        self.chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]

    def publish(self, post: Post) -> str:
        legenda = (
            f"*{post.corte}*\n\n"
            f"```\n{post.texto}\n```\n"
            f"_alt:_ {post.alt}"
        )
        with open(post.imagem, "rb") as img:
            r = requests.post(
                f"https://api.telegram.org/bot{self.token}/sendPhoto",
                data={"chat_id": self.chat_id, "caption": legenda,
                      "parse_mode": "Markdown"},
                files={"photo": img},
                timeout=60,
            )
        r.raise_for_status()
        return f"telegram:{r.json()['result']['message_id']}"


class ArquivoPublisher:
    """Fallback local: escreve o post ao lado do PNG. Serve para rodar sem segredo nenhum."""

    def publish(self, post: Post) -> str:
        destino = post.imagem.with_suffix(".txt")
        destino.write_text(
            f"{post.texto}\n\n---\nalt: {post.alt}\n", encoding="utf-8"
        )
        return f"arquivo:{destino}"


class XPublisher:
    def publish(self, post: Post) -> str:
        raise NotImplementedError(
            "A API do X é paga desde fev/2026 (pay-per-use, créditos pré-pagos). "
            "Implementar só quando o formato tiver provado que engaja — ver o plano."
        )


def escolher_publisher() -> Publisher:
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        return TelegramPublisher()
    return ArquivoPublisher()
