"""Os cortes — cada um vira um post.

O dado é MENSAL, mas o post é DIÁRIO. Isso significa que o bot não é um feed de
novidades: é um catálogo de cortes parametrizados sobre a mesma extração. Seis cortes
× (UF, CNAE, cidade) dá trinta posts sem repetir — e é assim que uma extração por mês
sustenta uma cadência diária sem mentir sobre a frequência do dado.
"""

import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path

from . import dados as D
from . import render, setores

MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

DUELOS = [("SP", "RJ"), ("MG", "BA"), ("RS", "PR"), ("PE", "CE"), ("SC", "GO")]


@dataclass
class Post:
    corte: str
    texto: str
    imagem: Path
    alt: str
    params: dict = field(default_factory=dict)


def _n(v: int) -> str:
    return f"{v:,}".replace(",", ".")


def _mes_ext(d: D.Dados) -> str:
    return f"{MESES[d.mes_ref.month]}/{d.mes_ref.year}"


def _fonte(d: D.Dados) -> str:
    return f"Dados abertos da Receita Federal, extração de {d.data_extracao:%d/%m/%Y}."


def placar_nacional(d: D.Dados, saida: Path) -> Post:
    mes = _mes_ext(d)
    total = D.total_mes(d, d.mes_ref)
    ufs = D.por_uf(d, d.mes_ref, limite=8)
    lider, n_lider = ufs[0]
    pct = 100 * n_lider / total

    img = render.ranking(
        saida / "placar_nacional.png",
        f"{_n(total)} empresas novas em {mes}",
        "Empresas ativas abertas no mês, por estado",
        ufs, d.data_extracao,
    )
    texto = (
        f"{_n(total)} empresas novas abriram no Brasil em {mes}.\n\n"
        f"{lider} sozinho respondeu por {_n(n_lider)} delas — {pct:.0f}% do país.\n\n"
        f"{_fonte(d)}"
    )
    alt = ("Gráfico de barras com as aberturas de empresas por estado em "
           f"{mes}. {'; '.join(f'{u}: {_n(v)}' for u, v in ufs)}.")
    return Post("placar_nacional", texto, img, alt)


def ranking_cnae(d: D.Dados, saida: Path, uf: str | None = None) -> Post:
    mes = _mes_ext(d)
    onde = uf or "no Brasil"
    itens = D.por_cnae(d, d.mes_ref, uf=uf, limite=8)
    topo, n_topo = itens[0]

    img = render.ranking(
        saida / f"ranking_cnae_{uf or 'BR'}.png",
        f"O que mais abriu {'em ' + uf if uf else 'no Brasil'} em {mes}",
        "Atividade principal declarada no CNPJ",
        itens, d.data_extracao,
    )
    texto = (
        f"A atividade que mais abriu empresa {'em ' + uf if uf else 'no Brasil'} "
        f"em {mes}:\n\n"
        f"{topo} — {_n(n_topo)} CNPJs novos.\n\n"
        f"O ranking completo dos 8 primeiros no gráfico.\n\n{_fonte(d)}"
    )
    alt = f"Ranking de atividades econômicas {onde} em {mes}. Topo: {topo}, {_n(n_topo)}."
    return Post("ranking_cnae", texto, img, alt, {"uf": uf})


def recorte_cidade(d: D.Dados, saida: Path, uf: str | None = None) -> Post:
    mes = _mes_ext(d)
    itens = D.por_municipio(d, d.mes_ref, uf=uf, limite=8)
    topo, n_topo = itens[0]

    img = render.ranking(
        saida / f"recorte_cidade_{uf or 'BR'}.png",
        f"As cidades que mais abriram empresa em {mes}",
        f"Municípios {'de ' + uf if uf else 'do Brasil'} por CNPJs novos",
        itens, d.data_extracao,
    )
    texto = (
        f"As cidades que mais abriram empresa em {mes}"
        f"{' (só ' + uf + ')' if uf else ''}:\n\n"
        f"1. {topo} — {_n(n_topo)}\n"
        f"2. {itens[1][0]} — {_n(itens[1][1])}\n"
        f"3. {itens[2][0]} — {_n(itens[2][1])}\n\n{_fonte(d)}"
    )
    alt = f"Ranking de municípios por aberturas em {mes}. Topo: {topo}, {_n(n_topo)}."
    return Post("recorte_cidade", texto, img, alt, {"uf": uf})


def setor_curioso(d: D.Dados, saida: Path, slug: str) -> Post:
    """Um setor específico, e onde ele mais abriu. É o corte que as pessoas compartilham."""
    mes = _mes_ext(d)
    setor = setores.POR_SLUG[slug]
    ufs = D.setor_por_uf(d, d.mes_ref, setor.codigos, limite=8)
    if not ufs:
        raise ValueError(f"nenhuma abertura para '{slug}' em {mes}")
    total = sum(v for _, v in ufs)
    lider, n_lider = ufs[0]

    img = render.ranking(
        saida / f"setor_{slug}.png",
        f"Onde abriram {setor.rotulo} em {mes}",
        f"{_n(total)} CNPJs novos com essa atividade, por estado",
        ufs, d.data_extracao,
        destaque=lider,  # um item É a história: destaca ele, apaga o resto
    )
    texto = (
        f"Abriram {_n(total)} {setor.rotulo} no Brasil em {mes}.\n\n"
        f"{lider} levou {_n(n_lider)} delas.\n\n{_fonte(d)}"
    )
    alt = (f"Aberturas de {setor.rotulo} por estado em {mes}. "
           f"Líder: {lider} com {_n(n_lider)}.")
    return Post("setor_curioso", texto, img, alt, {"setor": slug})


def duelo_regional(d: D.Dados, saida: Path, uf_a: str, uf_b: str) -> Post:
    """Duas séries de verdade -> categórico, com legenda."""
    mes = _mes_ext(d)
    topo_a = D.por_cnae(d, d.mes_ref, uf=uf_a, limite=5)
    cats = [c for c, _ in topo_a]

    vals_a = [v for _, v in topo_a]
    mapa_b = dict(D.por_cnae(d, d.mes_ref, uf=uf_b, limite=200))
    vals_b = [mapa_b.get(c, 0) for c in cats]

    img = render.comparacao(
        saida / f"duelo_{uf_a}_{uf_b}.png",
        f"{uf_a} x {uf_b}: o que cada um abriu em {mes}",
        f"Os 5 setores que mais abriram em {uf_a}, comparados com {uf_b}",
        cats, (uf_a, vals_a), (uf_b, vals_b), d.data_extracao,
    )
    texto = (
        f"{uf_a} x {uf_b} em {mes}: os cinco setores que mais abriram em {uf_a}, "
        f"e quanto {uf_b} abriu de cada um.\n\n{_fonte(d)}"
    )
    alt = f"Comparação de aberturas por setor entre {uf_a} e {uf_b} em {mes}."
    return Post("duelo_regional", texto, img, alt, {"uf_a": uf_a, "uf_b": uf_b})


def anomalia(d: D.Dados, saida: Path) -> Post:
    """O setor que mais cresceu vs o mês anterior."""
    mes = _mes_ext(d)
    anterior = (d.mes_ref - dt.timedelta(days=1)).replace(day=1)
    linhas = D.crescimento_cnae(d, d.mes_ref, anterior)
    if not linhas:
        raise ValueError("sem mês anterior no agregado para comparar")

    cnae, agora, antes, var = linhas[0]

    img = render.ranking(
        saida / "anomalia.png",
        f"O setor que mais acelerou em {mes}",
        f"+{var:.0f}% de aberturas contra o mês anterior",
        [(c, n) for c, n, _, _ in linhas], d.data_extracao,
        destaque=cnae,  # render encurta os dois com a mesma regra, então casa
    )
    texto = (
        f"O setor que mais acelerou em {mes}:\n\n"
        f"{cnae} — {_n(antes)} aberturas no mês anterior, {_n(agora)} agora. "
        f"+{var:.0f}%.\n\n{_fonte(d)}"
    )
    alt = f"Setores com maior crescimento de aberturas em {mes}. Topo: {cnae}, +{var:.0f}%."
    return Post("anomalia", texto, img, alt)
