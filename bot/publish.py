"""Para onde o post vai.

Esta é a costura que importa. O post vai direto para uma conta automatizada no X
(`XPublisher`). O `TelegramPublisher` fica como alternativa (era o plano antigo:
mandar para o celular e colar à mão) e o `ArquivoPublisher` como fallback local para
rodar sem segredo nenhum. `escolher_publisher()` decide pela ordem X → Telegram →
Arquivo conforme os segredos presentes no ambiente.

A API do X é paga desde fev/2026 (pay-per-use, créditos pré-pagos). Postar imagem são
duas chamadas: upload da mídia (v1.1, que também carrega o alt text) e criação do tweet
(v2). O `tweepy` cobre as duas.
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


_X_VARS = ("X_API_KEY", "X_API_SECRET", "X_ACCESS_TOKEN", "X_ACCESS_SECRET")


class XPublisher:
    """Posta imagem + texto direto numa conta automatizada do X.

    Auth é OAuth 1.0a (contexto de usuário) — é o que libera o upload de mídia v1.1,
    que por sua vez é o único jeito de anexar o texto ALT (acessibilidade). O tweet em
    si sai pela API v2.
    """

    def __init__(self, credenciais: dict[str, str] | None = None):
        c = credenciais or {v: os.environ[v] for v in _X_VARS}
        import tweepy  # dependência só deste caminho — o fallback local não a exige

        self._api = tweepy.API(tweepy.OAuth1UserHandler(
            c["X_API_KEY"], c["X_API_SECRET"],
            c["X_ACCESS_TOKEN"], c["X_ACCESS_SECRET"],
        ))
        self._client = tweepy.Client(
            consumer_key=c["X_API_KEY"], consumer_secret=c["X_API_SECRET"],
            access_token=c["X_ACCESS_TOKEN"], access_token_secret=c["X_ACCESS_SECRET"],
        )

    def publish(self, post: Post) -> str:
        # O texto do corte é escrito curto de propósito (< 280); se um dia passar, o X
        # rejeita e o Actions falha visível — melhor falhar que postar truncado.
        midia = self._api.media_upload(filename=str(post.imagem))
        self._api.create_media_metadata(midia.media_id, alt_text=post.alt)
        # Molde: quando houver CTA de landing, o link vai numa RESPOSTA a este tweet,
        # nunca no corpo (link no corpo corta o alcance) — usar in_reply_to_tweet_id.
        resp = self._client.create_tweet(text=post.texto, media_ids=[midia.media_id])
        return f"x:{resp.data['id']}"


def escolher_publisher() -> Publisher:
    if all(os.environ.get(v) for v in _X_VARS):
        return XPublisher()
    if os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID"):
        return TelegramPublisher()
    return ArquivoPublisher()
