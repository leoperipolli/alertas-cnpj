"""Tema visual dos posts.

O post é um PNG estático que vai cair no feed do X — sobre fundo branco para quem
usa o tema claro e sobre preto para quem usa o escuro. Não dá para ser "theme-aware":
a imagem tem que ter a própria superfície e funcionar nos dois. Escolhemos a superfície
clara, que é a validada com maior margem de separação para daltonismo.
"""

import re
from collections import Counter
from pathlib import Path

from matplotlib import font_manager as fm
from matplotlib import pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

# IBM Plex Sans (licença OFL) viaja no repo: assim a imagem sai IDÊNTICA no seu PC e
# no ubuntu do GitHub Actions — sem depender de "Segoe UI", que só existe no Windows e
# no CI cairia para outra fonte em silêncio. O SemiBold real também mata o aviso
# "Failed to find font weight 600".
_FONTS = Path(__file__).resolve().parent / "fonts"
for _ttf in sorted(_FONTS.glob("*.ttf")):
    fm.fontManager.addfont(str(_ttf))

# Paleta validada com scripts/validate_palette.js da skill dataviz (modo claro):
# verde×azul dá worst-adjacent CVD ΔE 22,7 (deutan) — bem acima do piso 8.
SUPERFICIE = "#fcfcfb"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
MUDO = "#898781"
GRADE = "#e1e0d9"
BORDA = "#c3c2b7"

# O molde pede um único acento, e fora do azul do Twitter (que some na UI do X).
SERIE_1 = "#2d7a3e"  # verde  — a cor de TODA barra de um ranking (o acento)
SERIE_2 = "#2a78d6"  # azul   — só quando há uma segunda série de verdade (duelo)
APAGADO = "#d8d7d1"  # o cinza do "resto" quando um item é a história (emphasis)

LARGURA_PX, ALTURA_PX = 1600, 900  # 16:9, o formato de imagem do X
DPI = 200

BARRA_PX = 24  # teto da espessura da barra; o resto da faixa é ar
RAIO_PX = 4    # ponta arredondada no lado do dado, quadrada na base


def usar_tema() -> None:
    plt.rcParams.update({
        "font.family": ["IBM Plex Sans", "DejaVu Sans"],
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
    domiciliar') e ninguém lê isso num gráfico.

    Para rótulo de EIXO prefira `rotulos_distintos` + `quebrar_rotulos`: cortar no
    caractere apaga justamente o fim, que é onde a descrição da Receita costuma
    guardar o que diferencia um CNAE do outro.
    """
    if len(texto) <= maximo:
        return texto
    corte = texto[:maximo].rsplit(" ", 1)[0]
    return (corte or texto[:maximo]).rstrip(",;") + "…"


# A descrição da Receita é formulaica: o miolo informativo vem primeiro e o rabo é
# jurídico ("não especificados anteriormente", "exceto produtos perigosos e mudanças").
# Tirar o rabo devolve espaço sem perder sentido.
_SEM_ESPEC = re.compile(r"\s*,?\s*n[ãa]o especificad[oa]s?\s+anteriormente", re.I)
_EXCETO = re.compile(r",\s*exceto\s+[^,]+?(?=,|$)", re.I)


def _variantes(texto: str) -> list[str]:
    """Da mais curta para a mais completa."""
    completo = texto.strip().rstrip(". ")
    sem_espec = _SEM_ESPEC.sub("", completo).strip().rstrip(",. ")
    sem_exceto = _EXCETO.sub("", sem_espec).strip().rstrip(",. ")
    return [sem_exceto, sem_espec, completo]


def limpar(texto: str) -> str:
    """Tira o rabo burocrático da descrição da Receita, sem quebrar linha.
    Para onde há uma linha só e espaço horizontal (o card em lista)."""
    return _variantes(texto)[0]


def rotulos_distintos(textos: list[str]) -> list[str]:
    """Encurta as descrições MAS garante que continuem diferentes entre si.

    Existe por um bug real: os dois maiores CNAEs de transporte são
    "...de carga, exceto produtos perigosos e mudanças, MUNICIPAL" e
    "...INTERMUNICIPAL, INTERESTADUAL E INTERNACIONAL". Cortados no caractere,
    viram o mesmo rótulo — e o gráfico mostra duas barras iguais com números
    diferentes, que é pior do que um rótulo comprido.

    Então: aplica-se a forma mais curta e, se duas colidirem, só as colididas
    sobem para uma forma mais completa até se separarem.
    """
    if not textos:
        return []
    variantes = [_variantes(t) for t in textos]
    escolha = [v[0] for v in variantes]
    for _ in range(len(variantes[0])):
        repetidos = {t for t, c in Counter(escolha).items() if c > 1}
        if not repetidos:
            break
        for i, v in enumerate(variantes):
            if escolha[i] in repetidos:
                escolha[i] = v[min(v.index(escolha[i]) + 1, len(v) - 1)]
    return escolha


def quebrar_rotulos(fig, textos: list[str], fontsize: int = 13,
                    alvo_frac: float = 0.32) -> list[str]:
    """Quebra cada rótulo em quantas linhas forem precisas. NUNCA trunca.

    Rótulo cortado é rótulo que mente: a descrição da Receita guarda no fim
    justamente o que separa um CNAE do outro. Quando o texto inteiro não cabe na
    altura disponível, quem cede é a QUANTIDADE DE BARRAS (ver `render._ajustar`),
    nunca o texto.
    """
    limite = alvo_frac * LARGURA_PX
    return ["\n".join(envolver(fig, t, fontsize, limite_px=limite)) for t in textos]


def _largura_px(fig, texto: str, fontsize: int) -> float:
    """Largura do texto em pixels, medida no renderer.

    O `canvas.draw()` redesenha a figura INTEIRA e custa dezenas de ms. Como a quebra
    de rótulo mede uma vez por palavra, desenhar a cada medição fazia o catálogo levar
    minutos (e o mesmo custo cairia no Actions todo dia). O renderer é o mesmo durante
    a vida da figura, então basta obtê-lo uma vez e guardar; as medidas também são
    memorizadas por (texto, corpo).
    """
    cache = getattr(fig, "_medidas", None)
    if cache is None:
        fig.canvas.draw()
        cache = fig._medidas = {"__renderer__": fig.canvas.get_renderer()}
    chave = (texto, fontsize)
    if chave not in cache:
        t = fig.text(0, 0, texto, fontsize=fontsize)
        cache[chave] = t.get_window_extent(renderer=cache["__renderer__"]).width
        t.remove()
    return cache[chave]


def eixos_com_rotulos(fig, rotulos: list[str], fontsize: int = 13, altura: float = 0.68):
    """Cria os eixos deixando espaço MEDIDO para os rótulos da esquerda.

    Margem fixa faz o rótulo longo ser cortado pela borda — e um rótulo cortado é
    pior do que rótulo nenhum. Aqui a margem é medida no renderer, não chutada.
    """
    # Mede LINHA a linha: com rótulo quebrado em duas, a largura que importa é a da
    # maior linha, não a do texto inteiro.
    maior = max((_largura_px(fig, linha, fontsize)
                 for r in rotulos for linha in r.split("\n")), default=0)
    esquerda = (0.055 * LARGURA_PX + maior + 16) / LARGURA_PX
    esquerda = min(esquerda, 0.46)  # teto: sobrou pouco para a barra, o gráfico morre
    return fig.add_axes([esquerda, 0.13, 0.975 - esquerda, altura])


def envolver(fig, texto: str, fontsize: int, max_frac: float = 0.89,
             limite_px: float | None = None) -> list[str]:
    """Quebra `texto` em linhas que cabem em `max_frac` da largura da figura
    (ou em `limite_px`, quando o orçamento é uma coluna e não a figura toda).

    `fig.text` não quebra linha sozinho: texto longo simplesmente sai pela borda
    direita da imagem (e sair pela borda é pior do que texto menor). A quebra é
    medida no renderer, não chutada por número de caracteres, porque a largura de um
    caractere depende da fonte.
    """
    limite = limite_px if limite_px is not None else max_frac * LARGURA_PX
    linhas: list[str] = []
    atual = ""
    for palavra in texto.split():
        tentativa = f"{atual} {palavra}".strip()
        if atual and _largura_px(fig, tentativa, fontsize) > limite:
            linhas.append(atual)
            atual = palavra
        else:
            atual = tentativa
    if atual:
        linhas.append(atual)
    return linhas or [texto]


def creditar(fig, data_extracao, fonte_extra: str | None = None) -> None:
    """A linha que vai em TODA peça, sem exceção.

    Honestidade de cadência (RNF-3): o dado é mensal na origem e a mensagem diz de
    quando ele é. É o que separa este bot de um raspador — e vira requisito do
    produto pago depois, então o hábito nasce aqui.

    `fonte_extra` acrescenta uma segunda fonte (ex.: "População: Censo IBGE 2022"
    nos cortes per capita) — um "por 100 mil hab" sem citar de onde vem a população
    queima credibilidade tanto quanto omitir a data da Receita.
    """
    linha = f"Dados abertos da Receita Federal · extração de {data_extracao:%d/%m/%Y}"
    if fonte_extra:
        linha += f" · {fonte_extra}"
    fig.text(0.055, 0.045, linha, fontsize=9, color=MUDO)


def titular(fig, titulo: str, subtitulo: str) -> None:
    """Título e subtítulo. O título ENCOLHE até caber na largura.

    Um título cortado pela borda direita da imagem é pior que um título menor — e
    acontece silenciosamente, porque `fig.text` não reclama de estouro. Então mede-se
    e reduz-se o corpo até caber (com piso, para não virar letra ilegível).
    """
    corpo = 25
    while corpo > 17 and _largura_px(fig, titulo, corpo) > 0.90 * LARGURA_PX:
        corpo -= 1
    fig.text(0.055, 0.93, titulo, fontsize=corpo, weight=600, color=TINTA, va="top")
    fig.text(0.055, 0.855, subtitulo, fontsize=13, color=TINTA_2, va="top")
