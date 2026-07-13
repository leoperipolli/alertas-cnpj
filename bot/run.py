"""Entrypoint do bot. Roda no GitHub Actions, 1x/dia.

    python -m bot.run                 # o corte do dia, publicado
    python -m bot.run --dry-run       # gera e mostra, sem publicar nem gastar o corte
    python -m bot.run --todos         # gera o catálogo inteiro em out/ (para revisar)
"""

import argparse
import sys
import traceback
from pathlib import Path

from . import agenda, dados, publish

SAIDA = Path(__file__).resolve().parent.parent / "out"


def um(dry_run: bool) -> int:
    d = dados.abrir()
    SAIDA.mkdir(parents=True, exist_ok=True)

    chave, funcao, estado = agenda.escolher(d)
    print(f"corte: {chave}  (extracao {d.data_extracao}, mes {d.mes_ref:%Y-%m})")
    post = funcao(SAIDA)

    print("\n" + "-" * 60)
    print(post.texto)
    print("-" * 60)
    print(f"imagem: {post.imagem}")

    if dry_run:
        print("\n[dry-run] nao publicou, nao gastou o corte")
        return 0

    ref = publish.escolher_publisher().publish(post)
    # Só agora: se a publicação falhar, o corte continua disponível amanhã.
    agenda.registrar(estado)
    print(f"publicado: {ref}")
    return 0


def todos() -> int:
    """Gera o catálogo inteiro de uma vez — é assim que você revisa antes de postar."""
    d = dados.abrir()
    SAIDA.mkdir(parents=True, exist_ok=True)
    ok = falhou = 0
    for chave, funcao in agenda.catalogo(d):
        try:
            post = funcao(SAIDA)
            publish.ArquivoPublisher().publish(post)
            print(f"  ok    {chave:28} -> {post.imagem.name}")
            ok += 1
        except Exception as e:
            print(f"  FALHA {chave:28} {type(e).__name__}: {e}")
            falhou += 1
    print(f"\n{ok} posts gerados em {SAIDA}" + (f", {falhou} falharam" if falhou else ""))
    return 1 if falhou else 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--todos", action="store_true")
    args = p.parse_args()
    try:
        sys.exit(todos() if args.todos else um(args.dry_run))
    except Exception:
        traceback.print_exc()
        sys.exit(1)  # falha visível: o Actions notifica (dead man's switch)
