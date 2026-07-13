"""Duas formas de gráfico. Só duas — e de propósito.

UF, CNAE e município são categorias NOMINAIS: não têm ordem natural. Pintar cada
barra de um tom diferente conforme o tamanho é anti-pattern — gasta o único canal
livre repetindo o que o comprimento da barra já diz, e a rampa fura os limites de
daltonismo por construção. Uma série, uma cor.

Quando um item É a história ("Sorocaba abriu mais petshop que Campinas"), a forma
certa não é colorir tudo: é dar destaque a ele e apagar o resto.
"""

from pathlib import Path

from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from . import tema


def _fmt(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def ranking(
    destino: Path,
    titulo: str,
    subtitulo: str,
    itens: list[tuple[str, int]],
    data_extracao,
    destaque: str | None = None,
) -> Path:
    """Barras horizontais, uma cor. `destaque` apaga o resto e realça um item."""
    fig = tema.nova_figura()

    itens = sorted(itens, key=lambda t: t[1], reverse=True)
    itens = [(tema.encurtar(r), v) for r, v in itens]
    if destaque is not None:
        destaque = tema.encurtar(destaque)
    maximo = max(v for _, v in itens) or 1
    ax = tema.eixos_com_rotulos(fig, [r for r, _ in itens])

    # Os limites vêm ANTES das barras: a espessura da barra é medida em pixels, e
    # sem os limites fixados a conversão pixel->dado usa a escala errada.
    ax.set_yticks(range(len(itens)))
    ax.set_yticklabels([r for r, _ in reversed(itens)], fontsize=13)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_xticks([])
    ax.set_xlim(0, maximo * 1.16)   # folga para o rótulo na ponta não estourar
    ax.set_ylim(-0.7, len(itens) - 0.3)
    px_x, px_y = tema.escala(ax)

    for i, (rotulo, valor) in enumerate(itens):
        y = len(itens) - 1 - i  # maior em cima
        cor = tema.SERIE_1
        if destaque is not None:
            cor = tema.SERIE_1 if rotulo == destaque else tema.APAGADO
        tema.barra_horizontal(ax, y, valor, cor, px_x, px_y)

        forte = destaque is None or rotulo == destaque
        ax.text(valor + maximo * 0.012, y, _fmt(valor),
                va="center", ha="left", fontsize=13,
                color=tema.TINTA if forte else tema.MUDO,
                weight=600 if forte else "normal")

    tema.titular(fig, titulo, subtitulo)
    tema.creditar(fig, data_extracao)
    fig.savefig(destino, dpi=tema.DPI)
    plt.close(fig)
    return destino


def comparacao(
    destino: Path,
    titulo: str,
    subtitulo: str,
    categorias: list[str],
    serie_a: tuple[str, list[int]],
    serie_b: tuple[str, list[int]],
    data_extracao,
) -> Path:
    """Duas séries de verdade -> categórico (2 slots), com legenda e rótulos.

    Os rótulos não são enfeite: o verde fica abaixo de 3:1 de contraste na superfície
    clara, e a regra de alívio da paleta exige rótulo visível quando isso acontece.
    """
    fig = tema.nova_figura()

    categorias = [tema.encurtar(c) for c in categorias]
    nome_a, vals_a = serie_a
    nome_b, vals_b = serie_b
    maximo = max([*vals_a, *vals_b]) or 1
    ax = tema.eixos_com_rotulos(fig, categorias, altura=0.66)

    ax.set_yticks(range(len(categorias)))
    ax.set_yticklabels(list(reversed(categorias)), fontsize=13)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_xticks([])
    ax.set_xlim(0, maximo * 1.16)
    ax.set_ylim(-0.8, len(categorias) - 0.2)
    px_x, px_y = tema.escala(ax)

    # 2px de superfície separando as barras vizinhas — o vão separa, não um contorno.
    meia = (tema.BARRA_PX / 2 + 1) / px_y

    for i, cat in enumerate(categorias):
        y = len(categorias) - 1 - i
        for valor, cor, deslocamento in (
            (vals_a[i], tema.SERIE_1, +meia),
            (vals_b[i], tema.SERIE_2, -meia),
        ):
            tema.barra_horizontal(ax, y + deslocamento, valor, cor, px_x, px_y)
            ax.text(valor + maximo * 0.012, y + deslocamento, _fmt(valor),
                    va="center", ha="left", fontsize=12, color=tema.TINTA)

    # Legenda sempre presente com 2+ séries: a identidade nunca depende só da cor.
    chaves = [Line2D([0], [0], marker="o", linestyle="none", markersize=9,
                     markerfacecolor=c, markeredgecolor="none", label=n)
              for n, c in ((nome_a, tema.SERIE_1), (nome_b, tema.SERIE_2))]
    leg = ax.legend(handles=chaves, loc="lower right", bbox_to_anchor=(1.0, 1.01),
                    ncol=2, frameon=False, fontsize=12, handletextpad=0.4,
                    columnspacing=1.6)
    for texto in leg.get_texts():
        texto.set_color(tema.TINTA_2)  # texto nunca veste a cor da série

    tema.titular(fig, titulo, subtitulo)
    tema.creditar(fig, data_extracao)
    fig.savefig(destino, dpi=tema.DPI)
    plt.close(fig)
    return destino
