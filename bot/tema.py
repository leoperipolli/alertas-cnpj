"""Tema visual dos posts.

O post é um PNG estático que vai cair no feed do X — sobre fundo branco para quem
usa o tema claro e sobre preto para quem usa o escuro. Não dá para ser "theme-aware":
a imagem tem que ter a própria superfície e funcionar nos dois. Escolhemos a superfície
clara, que é a validada com maior margem de separação para daltonismo.
"""

from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

# Paleta validada (worst adjacent CVD ΔE 73,6).
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
MUDO = "#898781"
GRADE = "#e1e0d9"
BORDA = "#c3c2b7"

SERIE_1 = "#2a78d6"  # azul   — a cor de TODA barra de um ranking
SERIE_2 = "#1baf7a"  # verde  — só quando há uma segunda série de verdade
APAGADO = "#d8d7d1"  # o cinza do "resto" quando um item é a história (emphasis)

LARGURA_PX, ALTURA_PX = 1600, 900  # 16:9, o formato de imagem do X
DPI = 200

BARRA_PX = 24  # teto da espessura da barra; o resto da faixa é ar
RAIO_PX = 4    # ponta arredondada no lado do dado, quadrada na base


def usar_tema() -> None:
    plt.rcParams.update({
        "font.family": ["Segoe UI", "DejaVu Sans"],
        "figure.facecolor": SUPERFICIE,
        "axes.facecolor": SUPERFICIE,
        "savefig.facecolor": SUPERFICIE,
        "text.color": TINTA,
        "axes.labelcolor": TINTA_2,
        "xtick.color": MUDO,
        "ytick.color": TINTA,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "axes.grid": False,
        "figure.dpi": DPI,
    })


def nova_figura():
    usar_tema()
    fig = plt.figure(figsize=(LARGURA_PX / DPI, ALTURA_PX / DPI))
    return fig


def escala(ax) -> tuple[float, float]:
    """Pixels por unidade de dado, em x e y.

    SÓ vale depois que xlim/ylim estão fixados. Chamar isto antes de fixar os
    limites devolve a escala dos limites padrão (0–1) e as barras saem com a
    espessura errada — foi exatamente esse o bug da primeira versão.
    """
    ax.figure.canvas.draw()
    p0 = ax.transData.transform((0, 0))
    p1 = ax.transData.transform((1, 1))
    return abs(p1[0] - p0[0]) or 1.0, abs(p1[1] - p0[1]) or 1.0


def barra_horizontal(ax, y: float, valor: float, cor: str,
                     px_por_x: float, px_por_y: float) -> None:
    """Barra com ponta arredondada no dado e quadrada na base.

    O arredondamento é em PIXELS, mas o patch vive em unidades de dados — e x e y
    têm escalas de pixel diferentes. `mutation_aspect` compensa isso; sem ele o
    canto vira uma elipse. A base é quadrada porque uma barra que cresce de um
    eixo não deve parecer flutuar.
    """
    altura = BARRA_PX / px_por_y          # 24px em unidades de dados y
    raio_x = RAIO_PX / px_por_x
    aspecto = px_por_x / px_por_y

    if valor <= 2 * raio_x:               # barra curta demais para arredondar
        ax.add_patch(Rectangle((0, y - altura / 2), valor, altura,
                               facecolor=cor, edgecolor="none", zorder=2))
        return

    ax.add_patch(FancyBboxPatch(
        (0, y - altura / 2), valor, altura,
        boxstyle=f"round,pad=0,rounding_size={raio_x}",
        mutation_aspect=aspecto,
        facecolor=cor, edgecolor="none", zorder=2,
    ))
    # Quadra a ponta encostada na linha de base.
    ax.add_patch(Rectangle((0, y - altura / 2), raio_x, altura,
                           facecolor=cor, edgecolor="none", zorder=3))


def encurtar(texto: str, maximo: int = 34) -> str:
    """Corta no limite de palavra. Descrição oficial de CNAE é impronunciável
    ('Fornecimento de alimentos preparados preponderantemente para consumo
    domiciliar') e ninguém lê isso num gráfico."""
    if len(texto) <= maximo:
        return texto
    corte = texto[:maximo].rsplit(" ", 1)[0]
    return (corte or texto[:maximo]).rstrip(",;") + "…"


def _largura_px(fig, texto: str, fontsize: int) -> float:
    t = fig.text(0, 0, texto, fontsize=fontsize)
    fig.canvas.draw()
    largura = t.get_window_extent(renderer=fig.canvas.get_renderer()).width
    t.remove()
    return largura


def eixos_com_rotulos(fig, rotulos: list[str], fontsize: int = 13, altura: float = 0.68):
    """Cria os eixos deixando espaço MEDIDO para os rótulos da esquerda.

    Margem fixa faz o rótulo longo ser cortado pela borda — e um rótulo cortado é
    pior do que rótulo nenhum. Aqui a margem é medida no renderer, não chutada.
    """
    maior = max((_largura_px(fig, r, fontsize) for r in rotulos), default=0)
    esquerda = (0.055 * LARGURA_PX + maior + 16) / LARGURA_PX
    esquerda = min(esquerda, 0.46)  # teto: sobrou pouco para a barra, o gráfico morre
    return fig.add_axes([esquerda, 0.13, 0.975 - esquerda, altura])


def creditar(fig, data_extracao) -> None:
    """A linha que vai em TODA peça, sem exceção.

    Honestidade de cadência (RNF-3): o dado é mensal na origem e a mensagem diz de
    quando ele é. É o que separa este bot de um raspador — e vira requisito do
    produto pago depois, então o hábito nasce aqui.
    """
    fig.text(0.055, 0.045,
             f"Dados abertos da Receita Federal · extração de "
             f"{data_extracao.strftime('%d/%m/%Y')}",
             fontsize=9, color=MUDO)


def titular(fig, titulo: str, subtitulo: str) -> None:
    fig.text(0.055, 0.93, titulo, fontsize=25, weight=600, color=TINTA,
             va="top")
    fig.text(0.055, 0.855, subtitulo, fontsize=13, color=TINTA_2, va="top")
