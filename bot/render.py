"""Duas formas de gráfico. Só duas — e de propósito.

UF, CNAE e município são categorias NOMINAIS: não têm ordem natural. Pintar cada
barra de um tom diferente conforme o tamanho é anti-pattern — gasta o único canal
livre repetindo o que o comprimento da barra já diz, e a rampa fura os limites de
daltonismo por construção. Uma série, uma cor.

Quando um item É a história ("Sorocaba abriu mais petshop que Campinas"), a forma
certa não é colorir tudo: é dar destaque a ele e apagar o resto.
"""

from pathlib import Path
from typing import Callable

import numpy as np
from matplotlib import pyplot as plt
from matplotlib.lines import Line2D

from . import tema


def _fmt(n: float) -> str:
    return f"{round(n):,}".replace(",", ".")


MINIMO_BARRAS = 5  # abaixo disso o ranking deixa de ser ranking


def _ajustar(fig, brutos: list[str], valores: list[float], altura_frac: float):
    """Acha quantas barras cabem com o rótulo INTEIRO — e devolve só essas.

    A regra é: o texto nunca encolhe nem some em reticências; quem cede é a
    quantidade de itens. Um rótulo de duas linhas precisa de ~2x a altura de faixa,
    e oito faixas não têm essa altura — então o ranking mostra seis, ou cinco.

    Descartar item é a ÚLTIMA concessão, não a primeira. Antes disso tenta, nesta
    ordem: reduzir o corpo da fonte (13 → 11) e alargar a coluna de rótulos (32% →
    38% da largura, o limite antes de a barra ficar curta demais). Só quando nada
    disso resolve é que a cauda cai.
    """
    tentativas = ((13, 0.32), (12, 0.32), (12, 0.38), (11, 0.32), (11, 0.38))
    while True:
        curtos = tema.rotulos_distintos(brutos)
        faixa_px = altura_frac * tema.ALTURA_PX / len(brutos)
        for corpo, alvo in tentativas:
            rotulos = tema.quebrar_rotulos(fig, curtos, fontsize=corpo, alvo_frac=alvo)
            linhas = max(r.count("\n") + 1 for r in rotulos)
            # altura de uma linha em px = corpo(pt) * DPI/72, com folga para o leading
            preciso_px = linhas * corpo * (tema.DPI / 72) * 1.18
            if preciso_px <= faixa_px:
                return brutos, valores, rotulos, corpo
        if len(brutos) <= MINIMO_BARRAS:
            return brutos, valores, rotulos, 11  # piso: aceita apertado
        brutos, valores = brutos[:-1], valores[:-1]


def fmt_decimal(casas: int = 1) -> Callable[[float], str]:
    """Formatador para valores fracionários (per capita, razões): '3,0', '5,8'.
    Vírgula decimal porque o público é brasileiro."""
    return lambda v: f"{v:.{casas}f}".replace(".", ",")


def ranking(
    destino: Path,
    titulo: str,
    subtitulo: str,
    itens: list[tuple[str, float]],
    data_extracao,
    destaque: str | None = None,
    fmt: Callable[[float], str] = _fmt,
    fonte_extra: str | None = None,
    altura: float = 0.68,
) -> Path:
    """Barras horizontais, uma cor. `destaque` apaga o resto e realça um item.

    `fmt` formata o rótulo do valor (inteiro por padrão; use `fmt_decimal()` no
    per capita/razão). `fonte_extra` acrescenta uma segunda fonte no crédito.

    ATENÇÃO: pode desenhar MENOS itens do que recebeu. Rótulo não é truncado; se os
    oito não couberem com o texto inteiro, o gráfico mostra os seis maiores. Por isso
    nenhum texto-alt deve enumerar todos os itens (ver `_ajustar`).
    """
    fig = tema.nova_figura()

    itens = sorted(itens, key=lambda t: t[1], reverse=True)
    brutos, valores, rotulos, corpo = _ajustar(
        fig, [r for r, _ in itens], [v for _, v in itens], altura)

    # O destaque é resolvido por ÍNDICE, sobre o rótulo original. Comparar o texto já
    # encurtado dependia de os dois passarem pela mesma regra de corte — e passou a
    # ser impossível quando o encurtamento virou quebra de linha.
    idx_destaque = brutos.index(destaque) if destaque in brutos else None

    maximo = max(valores) or 1
    ax = tema.eixos_com_rotulos(fig, rotulos, fontsize=corpo, altura=altura)

    # Os limites vêm ANTES das barras: a espessura da barra é medida em pixels, e
    # sem os limites fixados a conversão pixel->dado usa a escala errada.
    ax.set_yticks(range(len(valores)))
    ax.set_yticklabels(list(reversed(rotulos)), fontsize=corpo, linespacing=1.05)
    ax.tick_params(axis="y", length=0, pad=10)
    ax.set_xticks([])
    ax.set_xlim(0, maximo * 1.16)   # folga para o rótulo na ponta não estourar
    ax.set_ylim(-0.7, len(valores) - 0.3)
    px_x, px_y = tema.escala(ax)

    for i, valor in enumerate(valores):
        y = len(valores) - 1 - i  # maior em cima
        forte = idx_destaque is None or i == idx_destaque
        cor = tema.SERIE_1 if forte else tema.APAGADO
        tema.barra_horizontal(ax, y, valor, cor, px_x, px_y)

        ax.text(valor + maximo * 0.012, y, fmt(valor),
                va="center", ha="left", fontsize=13,
                color=tema.TINTA if forte else tema.MUDO,
                weight=600 if forte else "normal")

    tema.titular(fig, titulo, subtitulo)
    tema.creditar(fig, data_extracao, fonte_extra)
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

    nome_a, vals_a = serie_a
    nome_b, vals_b = serie_b
    # Duas séries por faixa: cada categoria come o dobro de altura, então cabe menos.
    # `_ajustar` corta a cauda; as duas séries têm que ser cortadas junto.
    categorias, vals_a, rotulos, corpo = _ajustar(fig, categorias, vals_a, 0.66 / 2)
    vals_b = vals_b[:len(categorias)]

    maximo = max([*vals_a, *vals_b]) or 1
    ax = tema.eixos_com_rotulos(fig, rotulos, fontsize=corpo, altura=0.66)

    ax.set_yticks(range(len(categorias)))
    ax.set_yticklabels(list(reversed(rotulos)), fontsize=corpo, linespacing=1.05)
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


def destaque_numero(
    destino: Path,
    titulo: str,
    numero: str,
    legenda: str,
    nota: str,
    data_extracao,
    fonte_extra: str | None = None,
) -> Path:
    """Número-herói: um único número enorme como foco.

    O molde do X premia tempo de permanência, e um número gigante é lido ANTES de
    qualquer gráfico — é o que faz o olho parar no scroll. Sem plot: é um 'stat tile',
    então nada de barras aqui. `nota` carrega a virada (ex.: 'SP é só o 10º')."""
    fig = tema.nova_figura()
    corpo_titulo = 26
    while corpo_titulo > 18 and \
            tema._largura_px(fig, titulo, corpo_titulo) > 0.90 * tema.LARGURA_PX:
        corpo_titulo -= 1
    fig.text(0.055, 0.92, titulo, fontsize=corpo_titulo, weight=600,
             color=tema.TINTA, va="top")

    # O bloco de texto é montado DE BAIXO PARA CIMA, a partir de um piso acima da
    # linha de crédito. Ancorar pelo topo estourava por baixo quando legenda e nota
    # quebravam em duas linhas cada — a última linha ia parar em cima do crédito.
    linhas_legenda = tema.envolver(fig, legenda, 20)
    linhas_nota = tema.envolver(fig, nota, 16)
    passo_legenda, passo_nota, folga = 0.068, 0.052, 0.014
    altura = (len(linhas_legenda) * passo_legenda + folga
              + len(linhas_nota) * passo_nota)
    piso = 0.135
    y = piso + altura

    # O número herói ocupa o que sobrou entre o título e o bloco, e encolhe se o
    # texto crescer. Assim ele é sempre o maior elemento da peça sem invadir nada.
    teto = 0.84
    espaco_px = max((teto - y), 0.1) * tema.ALTURA_PX
    corpo_numero = int(min(150, espaco_px * 0.86 / (tema.DPI / 72)))
    fig.text(0.055, (teto + y) / 2, numero, fontsize=corpo_numero, weight=600,
             color=tema.SERIE_1, va="center", ha="left")

    for linha in linhas_legenda:
        fig.text(0.055, y, linha, fontsize=20, color=tema.TINTA_2, va="top")
        y -= passo_legenda
    y -= folga
    for linha in linhas_nota:
        fig.text(0.055, y, linha, fontsize=16, color=tema.MUDO, va="top")
        y -= passo_nota

    tema.creditar(fig, data_extracao, fonte_extra)
    fig.savefig(destino, dpi=tema.DPI)
    plt.close(fig)
    return destino


def lista_cartao(
    destino: Path,
    titulo: str,
    subtitulo: str,
    linhas: list[tuple[str, str, str]],
    data_extracao,
    fonte_extra: str | None = None,
) -> Path:
    """Card em lista: uma linha por item (esquerda em negrito, meio, valor à direita).

    É a forma certa para 'o setor-assinatura de cada estado' — não é ranking de uma
    grandeza só, é um par estado→setor por linha. Um mapa exigiria shapefile; a lista
    diz o mesmo e é legível no thumbnail."""
    fig = tema.nova_figura()
    tema.titular(fig, titulo, subtitulo)

    # Espaçamento FIXO com o bloco centralizado na área útil. Esticar as linhas para
    # preencher a altura funciona com 8 itens e vira um vão absurdo com 2 — o card da
    # "dupla" tem exatamente 2.
    topo, base = 0.74, 0.135
    passo = min(0.085, (topo - base) / max(len(linhas) - 1, 1))
    inicio = topo - ((topo - base) - passo * (len(linhas) - 1)) / 2
    ys = [inicio - passo * i for i in range(len(linhas))]
    for (esq, meio, val), y in zip(linhas, ys):
        fig.text(0.055, y, esq, fontsize=17, weight=600, color=tema.TINTA, va="center")
        fig.text(0.135, y, tema.encurtar(tema.limpar(meio), 48), fontsize=15,
                 color=tema.TINTA_2, va="center")
        fig.text(0.945, y, val, fontsize=17, weight=600, color=tema.SERIE_1,
                 va="center", ha="right")

    tema.creditar(fig, data_extracao, fonte_extra)
    fig.savefig(destino, dpi=tema.DPI)
    plt.close(fig)
    return destino


def dispersao(
    destino: Path,
    titulo: str,
    subtitulo: str,
    pontos: list[tuple[str, float, float]],
    rotulo_x: str,
    rotulo_y: str,
    data_extracao,
    rotular: set[str] | None = None,
) -> Path:
    """Dispersão UF a UF com reta de tendência — a forma do 'gráfico espúrio'.

    Dois setores sem relação nenhuma que andam juntos entre estados: a reta quase
    perfeita É a piada, e o disclaimer 'correlação não é causa' vai na legenda do
    post."""
    fig = tema.nova_figura()
    rotular = rotular or set()
    # Base alta o bastante para o rótulo do eixo X não encostar na linha de crédito.
    ax = fig.add_axes([0.085, 0.205, 0.88, 0.565])

    xs = [x for _, x, _ in pontos]
    ys = [y for _, _, y in pontos]

    # Reta de tendência primeiro (zorder baixo), pontos por cima.
    if len(xs) >= 2:
        a, b = np.polyfit(xs, ys, 1)
        lo, hi = min(xs), max(xs)
        ax.plot([lo, hi], [a * lo + b, a * hi + b], color=tema.APAGADO,
                linewidth=2, zorder=1)
    # Anel de 2px na cor da superfície separa pontos que se encostam.
    ax.scatter(xs, ys, s=110, color=tema.SERIE_1, edgecolor=tema.SUPERFICIE,
               linewidth=1.5, zorder=3)

    for uf, x, y in pontos:
        if uf in rotular:
            ax.annotate(uf, (x, y), textcoords="offset points", xytext=(7, 5),
                        fontsize=12, color=tema.TINTA_2, weight=600)

    ax.set_xlabel(rotulo_x, fontsize=12, color=tema.TINTA_2)
    ax.set_ylabel(rotulo_y, fontsize=12, color=tema.TINTA_2)
    ax.tick_params(length=0, labelsize=10, colors=tema.MUDO)
    ax.grid(True, color=tema.GRADE, linewidth=0.8, zorder=0)
    ax.margins(0.08)

    tema.titular(fig, titulo, subtitulo)
    tema.creditar(fig, data_extracao)
    fig.savefig(destino, dpi=tema.DPI)
    plt.close(fig)
    return destino
