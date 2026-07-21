"""População por UF — Censo IBGE 2022 (resultados do universo).

Existe para os cortes "per capita": o dado da Receita é contagem absoluta, e absoluto
é sempre liderado por SP porque SP tem mais gente. Dividir por habitante é o que revela
a história ("a capital do boteco é o Espírito Santo") — e é o que engaja.

Estático de propósito: a população de um censo não muda mês a mês, e uma tabela no
código não precisa de download, de ETL nem de rede. A pseudo-UF `EX` (exterior) NÃO
entra aqui — e é por isso que os cortes per capita a excluem de graça (o join derruba
quem não tem população).

Fonte: IBGE, Censo Demográfico 2022 (população residente por Unidade da Federação).
"""

POPULACAO_UF: dict[str, int] = {
    "SP": 44_411_238,
    "MG": 20_538_718,
    "RJ": 16_054_524,
    "BA": 14_141_626,
    "PR": 11_444_380,
    "RS": 10_882_965,
    "PE": 9_058_931,
    "CE": 8_794_957,
    "PA": 8_120_131,
    "SC": 7_610_361,
    "GO": 7_056_495,
    "MA": 6_776_699,
    "PB": 3_974_687,
    "AM": 3_941_613,
    "ES": 3_833_712,
    "MT": 3_658_649,
    "RN": 3_302_406,
    "PI": 3_269_200,
    "AL": 3_127_683,
    "DF": 2_817_381,
    "MS": 2_757_013,
    "SE": 2_209_558,
    "RO": 1_581_196,
    "TO": 1_511_460,
    "AC": 830_018,
    "AP": 733_759,
    "RR": 636_707,
}

FONTE = "População: Censo IBGE 2022"


def por_100k(contagem: int, uf: str) -> float | None:
    """Aberturas por 100 mil habitantes. None se a UF não tem população conhecida
    (ex.: `EX`) — o chamador descarta essas."""
    hab = POPULACAO_UF.get(uf)
    if not hab:
        return None
    return contagem * 100_000 / hab
