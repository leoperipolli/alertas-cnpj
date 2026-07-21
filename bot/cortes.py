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
from . import populacao, render, setores, tema

MESES = ["", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

DUELOS = [("SP", "RJ"), ("MG", "BA"), ("RS", "PR"), ("PE", "CE"), ("SC", "GO")]


LIMITE_TEXTO = 280   # limite de um post no X
LIMITE_ALT = 1000    # limite do texto alternativo de mídia no X


@dataclass
class Post:
    corte: str
    texto: str
    imagem: Path
    alt: str
    params: dict = field(default_factory=dict)

    def __post_init__(self):
        """Estoura na GERAÇÃO, não na publicação.

        Um texto de 281 caracteres só falharia lá na frente, no X, com o corte já
        gasto e o Actions vermelho de madrugada. Aqui `--todos` acusa na hora, antes
        de qualquer coisa ir ao ar. Nome do mês e nome de estado variam de tamanho a
        cada extração, então isto não é hipotético: é o jeito de a copy não quebrar
        sozinha em agosto.
        """
        if len(self.texto) > LIMITE_TEXTO:
            raise ValueError(
                f"corte '{self.corte}': texto com {len(self.texto)} caracteres "
                f"(limite {LIMITE_TEXTO}). Encurte a copy."
            )
        if len(self.alt) > LIMITE_ALT:
            raise ValueError(
                f"corte '{self.corte}': alt com {len(self.alt)} caracteres "
                f"(limite {LIMITE_ALT})."
            )


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
        f"Um estado só concentra {pct:.0f}% das aberturas. Isso é demais?\n\n"
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
    # A descrição oficial de CNAE tem tamanho imprevisível ("Fornecimento de alimentos
    # preparados preponderantemente para consumo domiciliar"). Sem encurtar, o texto
    # estoura o limite do X dependendo de qual setor liderou — falha dependente do dado.
    texto = (
        f"A atividade que mais abriu empresa {'em ' + uf if uf else 'no Brasil'} "
        f"em {mes}:\n\n"
        f"{tema.encurtar(topo, 60)} — {_n(n_topo)} CNPJs novos.\n\n"
        f"Esperava ver esse setor no topo?\n\n{_fonte(d)}"
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
        f"3. {itens[2][0]} — {_n(itens[2][1])}\n\n"
        f"Sua cidade entrou na lista?\n\n{_fonte(d)}"
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
        f"{lider} levou {_n(n_lider)} delas.\n\n"
        f"Faz sentido {lider} liderar em {setor.rotulo}?\n\n{_fonte(d)}"
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
        f"e quanto {uf_b} abriu de cada um.\n\n"
        f"Quem você achava que abriria mais?\n\n{_fonte(d)}"
    )
    alt = f"Comparação de aberturas por setor entre {uf_a} e {uf_b} em {mes}."
    return Post("duelo_regional", texto, img, alt, {"uf_a": uf_a, "uf_b": uf_b})


TETO_RECLASSIFICACAO = 200  # %


def anomalia(d: D.Dados, saida: Path) -> Post:
    """O setor que mais cresceu vs o mês anterior — com guarda contra reclassificação.

    Um salto de 3x+ num único mês quase nunca é tendência econômica: é a Receita
    reclassificando um CNAE ou soltando um lote de cadastros represados (em jun/2026,
    'laticínios e frios' saltou +397% assim). Postar isso como 'o setor que bombou'
    queima credibilidade. Então acima de +200% a linha é descartada por suspeita — o
    herói do post é o maior crescimento *plausível*.
    """
    mes = _mes_ext(d)
    anterior = (d.mes_ref - dt.timedelta(days=1)).replace(day=1)
    linhas = D.crescimento_cnae(d, d.mes_ref, anterior)
    if not linhas:
        raise ValueError("sem mês anterior no agregado para comparar")

    plausiveis = [l for l in linhas if l[3] <= TETO_RECLASSIFICACAO] or linhas
    cnae, agora, antes, var = plausiveis[0]

    img = render.ranking(
        saida / "anomalia.png",
        f"O setor que mais acelerou em {mes}",
        f"+{var:.0f}% de aberturas contra o mês anterior",
        [(c, n) for c, n, _, _ in plausiveis], d.data_extracao,
        destaque=cnae,  # render encurta os dois com a mesma regra, então casa
    )
    texto = (
        f"O setor que mais acelerou em {mes}:\n\n"
        f"{tema.encurtar(cnae, 55)} — {_n(antes)} aberturas no mês anterior, "
        f"{_n(agora)} agora. +{var:.0f}%.\n\n"
        f"Alguém arrisca por quê?\n\n{_fonte(d)}"
    )
    alt = f"Setores com maior crescimento de aberturas em {mes}. Topo: {cnae}, +{var:.0f}%."
    return Post("anomalia", texto, img, alt)


# --------------------------------------------------------------------------------
# Cortes contraintuitivos.
#
# Os cortes acima são honestos mas óbvios: em número absoluto SP lidera tudo, porque
# SP tem mais gente. "Abriu mais petshop em SP" não gera reply nenhum. Os cortes
# abaixo existem para produzir a virada — normalizar (por habitante, por outro setor,
# pela fatia nacional) é o que derruba SP do topo e faz o post ser compartilhado.
# --------------------------------------------------------------------------------

def _dec(v: float) -> str:
    return render.fmt_decimal(1)(v)


def _por_capita(itens: list[tuple[str, int]], piso: int = 0) -> list[tuple[str, float, int]]:
    """(uf, por_100k, bruto) ordenado do maior para o menor.

    `piso` descarta UF com pouca abertura no setor: sem ele, um estado pequeno com 6
    aberturas lidera o "por habitante" por acaso e o post vira ruído estatístico.
    UF sem população conhecida (a pseudo-UF `EX`) cai fora sozinha.
    """
    out = [(uf, r, n) for uf, n in itens
           if n >= piso and (r := populacao.por_100k(n, uf)) is not None]
    out.sort(key=lambda t: t[1], reverse=True)
    return out


def ranking_per_capita(d: D.Dados, saida: Path, slug: str | None = None,
                       piso: int = 20) -> Post:
    """Aberturas por 100 mil habitantes. O corte que tira SP do topo."""
    mes = _mes_ext(d)
    if slug:
        setor = setores.POR_SLUG[slug]
        rotulo = setor.rotulo
        brutos = D.setor_por_uf_completo(d, d.mes_ref, setor.codigos)
        titulo = f"Onde mais se abre {rotulo} por habitante"
        subtitulo = f"Aberturas de {rotulo} por 100 mil habitantes em {mes}"
    else:
        rotulo = "empresa"
        brutos = D.total_por_uf(d, d.mes_ref)
        titulo = "Onde mais se abre empresa por habitante"
        subtitulo = f"Empresas novas por 100 mil habitantes em {mes}"

    pc = _por_capita(brutos, piso)
    if not pc:
        raise ValueError(f"sem dado per capita para '{slug or 'total'}'")

    lider, taxa, _ = pc[0]
    ordem = [uf for uf, _, _ in pc]
    pos_sp = ordem.index("SP") + 1 if "SP" in ordem else None

    img = render.ranking(
        saida / f"percapita_{slug or 'total'}.png", titulo, subtitulo,
        [(uf, r) for uf, r, _ in pc[:8]], d.data_extracao,
        destaque=lider, fmt=render.fmt_decimal(1), fonte_extra=populacao.FONTE,
    )

    virada = f"São Paulo, o maior do país, é só o {pos_sp}º." if pos_sp else ""
    # A fonte da população não repete no texto: ela já vai no crédito da imagem, e
    # aqui cada caractere disputa o limite de 280 do X.
    texto = (
        f"Quem mais abre {rotulo} por habitante no Brasil é {lider}: "
        f"{_dec(taxa)} por 100 mil hab em {mes}.\n\n"
        f"{virada}\n\n"
        f"Você imaginava {lider} na frente de SP?\n\n"
        f"{_fonte(d)}"
    )
    alt = (f"Aberturas de {rotulo} por 100 mil habitantes por estado em {mes}. "
           f"Líder: {lider} com {_dec(taxa)}"
           + (f"; São Paulo em {pos_sp}º." if pos_sp else "."))
    return Post("ranking_per_capita", texto, img, alt, {"setor": slug})


def razao_setores(d: D.Dados, saida: Path, chave: str, titulo: str, subtitulo: str,
                  slugs_num: list[str], slugs_den: list[str], frase: str,
                  pergunta: str, piso_den: int = 20) -> Post:
    """Quantos X abrem para cada Y — o "índice" com nome engraçado.

    `piso_den` é obrigatório por construção: com denominador pequeno a razão explode
    (2 academias num estado viram "15 bares por academia") e o ranking vira artefato.
    """
    mes = _mes_ext(d)
    cods_num = [c for s in slugs_num for c in setores.POR_SLUG[s].codigos]
    cods_den = [c for s in slugs_den for c in setores.POR_SLUG[s].codigos]
    num = dict(D.setor_por_uf_completo(d, d.mes_ref, cods_num))
    den = dict(D.setor_por_uf_completo(d, d.mes_ref, cods_den))

    razoes = [(uf, num.get(uf, 0) / n) for uf, n in den.items()
              if n >= piso_den and num.get(uf, 0) > 0]
    if not razoes:
        raise ValueError(f"sem razão calculável para '{chave}'")
    razoes.sort(key=lambda t: t[1], reverse=True)

    lider, r = razoes[0]
    titulo, subtitulo = titulo.format(mes=mes), subtitulo.format(mes=mes)
    img = render.ranking(
        saida / f"razao_{chave}.png", titulo, subtitulo, razoes[:8],
        d.data_extracao, destaque=lider, fmt=render.fmt_decimal(1),
    )
    texto = (f"{frase.format(lider=lider, r=_dec(r), mes=mes)}\n\n"
             f"{pergunta}\n\n{_fonte(d)}")
    alt = f"{titulo} por estado em {mes}. Líder: {lider} com {_dec(r)}."
    return Post("razao_setores", texto, img, alt, {"chave": chave})


def dupla_per_capita(d: D.Dados, saida: Path, slug_a: str, slug_b: str,
                     foco: str = "DF") -> Post:
    """Um estado no topo de dois setores que não deveriam andar juntos (ideia 9).

    O rodapé "correlação não é causa" não é piada defensiva: é o que torna o post
    discutível sem ser desonesto — e discussão é reply.
    """
    mes = _mes_ext(d)

    def rank_taxa(slug: str) -> tuple[str, int | None, float | None]:
        setor = setores.POR_SLUG[slug]
        pc = _por_capita(D.setor_por_uf_completo(d, d.mes_ref, setor.codigos))
        ordem = [uf for uf, _, _ in pc]
        taxa = next((r for uf, r, _ in pc if uf == foco), None)
        return setor.rotulo, (ordem.index(foco) + 1 if foco in ordem else None), taxa

    rot_a, pos_a, ta = rank_taxa(slug_a)
    rot_b, pos_b, tb = rank_taxa(slug_b)
    if ta is None or tb is None:
        raise ValueError(f"{foco} sem dado em '{slug_a}' ou '{slug_b}'")

    linhas = [(f"{pos_a}º", f"{foco} em {rot_a}", _dec(ta)),
              (f"{pos_b}º", f"{foco} em {rot_b}", _dec(tb))]
    img = render.lista_cartao(
        saida / f"dupla_{foco}.png",
        f"{foco} no topo de duas coisas que não combinam",
        f"Posição e aberturas por 100 mil habitantes em {mes}",
        linhas, d.data_extracao, fonte_extra=populacao.FONTE,
    )
    texto = (
        f"Coincidência de {mes}: {foco} está no topo do país ao mesmo tempo em "
        f"{rot_a} e em {rot_b}, por habitante.\n\n"
        f"Correlação não é causa.\n\n"
        f"O que explica {foco} liderar os dois?\n\n"
        f"{_fonte(d)}"
    )
    alt = (f"{foco} aparece em {pos_a}º em {rot_a} e em {pos_b}º em {rot_b} "
           f"por 100 mil habitantes, {mes}.")
    return Post("dupla_per_capita", texto, img, alt, {"foco": foco})


def setor_assinatura(d: D.Dados, saida: Path) -> Post:
    """O setor que cada estado abre muito acima da média nacional (ideia 13).

    Dedup por descrição de propósito: sem isso três estados do Nordeste aparecem com
    "representantes comerciais" e o card perde a graça — a graça é a variedade.
    """
    mes = _mes_ext(d)
    vistos_uf: set[str] = set()
    vistas_desc: set[str] = set()
    linhas: list[tuple[str, str, str]] = []

    for uf, _cod, dsc, _n, _tcn, lq in D.location_quotient(d, d.mes_ref):
        if uf in vistos_uf:
            continue
        chave = dsc.split(",")[0][:22].lower()
        if chave in vistas_desc:
            continue
        vistos_uf.add(uf)
        vistas_desc.add(chave)
        linhas.append((uf, dsc, f"{lq:.0f}×"))
        if len(linhas) >= 8:
            break

    if not linhas:
        raise ValueError("sem location quotient com base suficiente")

    img = render.lista_cartao(
        saida / "setor_assinatura.png",
        "O que cada estado abre muito acima da média",
        f"Setor mais sobre-representado de cada estado em {mes} (× a média nacional)",
        linhas, d.data_extracao,
    )
    uf_topo, dsc_topo, lq_topo = linhas[0]
    texto = (
        f"O que cada estado abre MUITO acima da média do Brasil, em {mes}.\n\n"
        f"O caso mais extremo: {uf_topo}, com {lq_topo} a média nacional em "
        f"{tema.encurtar(dsc_topo, 40).lower()}.\n\n"
        f"Achou a cara do seu estado?\n\n{_fonte(d)}"
    )
    alt = ("Setor mais sobre-representado de cada estado em " + mes + ": "
           + "; ".join(f"{u}: {t}" for u, _, t in linhas) + ".")
    return Post("setor_assinatura", texto, img, alt)


def lq_hero(d: D.Dados, saida: Path, chave: str, codigos: list[str],
            rotulo: str, piso: int = 10) -> Post:
    """Número-herói: quantas vezes a média nacional o estado mais desproporcional
    abre de um setor.

    Sobre-representação (LQ) não é "por habitante": é a fatia daquele setor dentro
    das aberturas do estado, comparada à fatia dele no Brasil. Por isso o texto diz
    "proporcionalmente", nunca "por habitante" — trocar os dois é errar o número.

    O líder é DESCOBERTO, nunca fixado no código: quem lidera muda de extração para
    extração, e um herói hardcodado viraria post falso no mês seguinte. O `piso`
    evita que um estado com 3 aberturas estoure a razão e vire "o estado do táxi".
    """
    mes = _mes_ext(d)
    setor = dict(D.setor_por_uf_completo(d, d.mes_ref, codigos))
    total = dict(D.total_por_uf(d, d.mes_ref))
    s_br, t_br = sum(setor.values()), sum(total.values())
    if not s_br:
        raise ValueError(f"sem aberturas de '{rotulo}' em {mes}")

    lqs = sorted(
        ((uf, (n / total[uf]) / (s_br / t_br), n) for uf, n in setor.items()
         if n >= piso and total.get(uf)),
        key=lambda t: t[1], reverse=True,
    )
    if len(lqs) < 2:
        raise ValueError(f"base insuficiente para o LQ de '{rotulo}'")

    uf, lq, n = lqs[0]
    uf_2, lq_2, _ = lqs[1]

    img = render.destaque_numero(
        saida / f"lqhero_{chave}.png",
        f"{uf} é o estado do {rotulo}",
        f"{lq:.0f}×",
        f"o que {uf} abre de {rotulo}, proporcionalmente, contra a média do Brasil",
        f"São {n} aberturas em {mes}. O 2º colocado, {uf_2}, abre {_dec(lq_2)}× a média.",
        d.data_extracao,
    )
    texto = (
        f"O estado que proporcionalmente mais abre {rotulo} no Brasil é {uf}: "
        f"{_dec(lq)}× a média nacional em {mes}.\n\n"
        f"Não é o maior número absoluto — é o mais desproporcional. "
        f"O 2º, {uf_2}, fica em {_dec(lq_2)}×.\n\n"
        f"Alguém arrisca por quê?\n\n{_fonte(d)}"
    )
    alt = (f"{uf} abre {_dec(lq)} vezes mais {rotulo} que a média nacional, "
           f"proporcionalmente, em {mes}; 2º é {uf_2} com {_dec(lq_2)}.")
    return Post("lq_hero", texto, img, alt, {"chave": chave})


def correlacao_espuria(d: D.Dados, saida: Path, chave: str,
                       slug_a: str, slug_b: str) -> Post:
    """Dois setores sem relação que andam juntos entre estados (ideia 10).

    A correlação é real e a causa é boba: os dois crescem com o tamanho do estado.
    Usa contagem BRUTA de propósito — normalizar por habitante mataria justamente o
    efeito que é a piada.
    """
    mes = _mes_ext(d)
    sa, sb = setores.POR_SLUG[slug_a], setores.POR_SLUG[slug_b]
    a = dict(D.setor_por_uf_completo(d, d.mes_ref, sa.codigos))
    b = dict(D.setor_por_uf_completo(d, d.mes_ref, sb.codigos))
    pontos = [(uf, a[uf], b[uf]) for uf in a if uf in b]
    if len(pontos) < 5:
        raise ValueError(f"poucos pontos para '{chave}'")

    img = render.dispersao(
        saida / f"espuria_{chave}.png",
        "Duas coisas sem relação que andam juntas",
        f"Cada ponto é um estado — aberturas em {mes}",
        pontos, sa.rotulo.capitalize(), sb.rotulo.capitalize(),
        d.data_extracao, rotular={"SP", "MG", "RJ"},
    )
    texto = (
        f"{sa.rotulo.capitalize()} e {sb.rotulo} não têm nada a ver.\n\n"
        f"Mesmo assim andam juntos entre os estados — a linha é quase perfeita. "
        f"A causa escondida é o tamanho do estado.\n\n"
        f"Correlação não é causa.\n\n{_fonte(d)}"
    )
    alt = (f"Dispersão por estado de {sa.rotulo} contra {sb.rotulo} em {mes}: "
           f"correlação alta e espúria.")
    return Post("correlacao_espuria", texto, img, alt, {"chave": chave})
