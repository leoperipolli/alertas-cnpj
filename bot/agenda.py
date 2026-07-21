"""Qual corte sai hoje.

Estado num JSON commitado — não precisa de banco. A regra é simples: nunca repetir
um corte enquanto houver corte novo no catálogo, e zerar o catálogo quando chega uma
extração nova (o dado mudou, então os mesmos cortes voltam a ser notícia).
"""

import json
from pathlib import Path

from . import cortes, setores

ESTADO = Path(__file__).resolve().parent.parent / "data" / "agenda_estado.json"


def _contraintuitivos(d) -> list[tuple[str, callable]]:
    """Os cortes que tiram SP do topo — e por isso vão PRIMEIRO na rotação.

    A conta do X é nova: os primeiros posts é que constroem a primeira impressão.
    Estrear com "SP abriu 31% das empresas" é verdadeiro, óbvio e não gera reply
    nenhum. Estes viram a mesa (por habitante, por outro setor, pela fatia nacional).

    Os pisos (`piso`, `piso_den`) são calibrados por setor: quanto menor o volume
    nacional do setor, mais fácil um estado pequeno liderar por acaso.
    """
    return [
        ("percapita|total", lambda saida: cortes.ranking_per_capita(d, saida)),
        ("percapita|bar",
         lambda saida: cortes.ranking_per_capita(d, saida, "bar", piso=25)),
        ("assinatura", lambda saida: cortes.setor_assinatura(d, saida)),
        ("razao|bar-academia", lambda saida: cortes.razao_setores(
            d, saida, "bar-academia",
            "Bares por academia",
            "Quantos bares novos abrem para cada academia nova em {mes}",
            ["bar"], ["academia"],
            "Em {lider}, abrem {r} bares novos para cada academia nova.",
            "O seu estado escolhe o happy hour ou a esteira?", piso_den=15)),
        ("lqhero|taxi", lambda saida: cortes.lq_hero(
            d, saida, "taxi", ["4923001"], "táxi")),
        ("percapita|salao-de-beleza",
         lambda saida: cortes.ranking_per_capita(d, saida, "salao-de-beleza", piso=50)),
        ("espuria|padaria-psicologia", lambda saida: cortes.correlacao_espuria(
            d, saida, "padaria-psicologia", "padaria", "psicologia")),
        ("percapita|restaurante",
         lambda saida: cortes.ranking_per_capita(d, saida, "restaurante", piso=30)),
        ("dupla|DF", lambda saida: cortes.dupla_per_capita(
            d, saida, "salao-de-beleza", "psicologia", "DF")),
        ("razao|social-psicologia", lambda saida: cortes.razao_setores(
            d, saida, "social-psicologia",
            "Bar e restaurante por psicólogo",
            "Bares e restaurantes novos para cada consultório de psicologia em {mes}",
            ["bar", "restaurante"], ["psicologia"],
            "Em {lider}, abrem {r} bares e restaurantes para cada "
            "consultório de psicologia.",
            "Seu estado resolve no boteco ou no divã?", piso_den=40)),
        ("percapita|academia",
         lambda saida: cortes.ranking_per_capita(d, saida, "academia", piso=15)),
        ("razao|padaria-petshop", lambda saida: cortes.razao_setores(
            d, saida, "padaria-petshop",
            "Padarias por petshop",
            "Quantas padarias novas abrem para cada petshop novo em {mes}",
            ["padaria"], ["petshop"],
            "Em {lider}, ainda abrem {r} padarias para cada petshop.",
            "O pet vai passar a padaria no seu estado?", piso_den=25)),
    ]


def catalogo(d) -> list[tuple[str, callable]]:
    """~45 posts a partir de 12 cortes. É a parametrização que sustenta a cadência diária."""
    itens: list[tuple[str, callable]] = [
        *_contraintuitivos(d),
        ("placar_nacional", lambda saida: cortes.placar_nacional(d, saida)),
        ("ranking_cnae|BR", lambda saida: cortes.ranking_cnae(d, saida)),
        ("recorte_cidade|BR", lambda saida: cortes.recorte_cidade(d, saida)),
        ("anomalia", lambda saida: cortes.anomalia(d, saida)),
    ]
    for s in setores.SETORES:
        itens.append((f"setor|{s.slug}",
                      lambda saida, sl=s.slug: cortes.setor_curioso(d, saida, sl)))
    for uf in ["SP", "MG", "RJ", "BA", "PR", "RS"]:
        itens.append((f"ranking_cnae|{uf}",
                      lambda saida, u=uf: cortes.ranking_cnae(d, saida, u)))
        itens.append((f"recorte_cidade|{uf}",
                      lambda saida, u=uf: cortes.recorte_cidade(d, saida, u)))
    for a, b in cortes.DUELOS:
        itens.append((f"duelo|{a}x{b}",
                      lambda saida, x=a, y=b: cortes.duelo_regional(d, saida, x, y)))
    return itens


def _ler(data_extracao) -> dict:
    if not ESTADO.exists():
        return {"data_extracao": str(data_extracao), "usados": []}
    est = json.loads(ESTADO.read_text(encoding="utf-8"))
    if est.get("data_extracao") != str(data_extracao):
        # Extração nova: o catálogo inteiro volta a valer.
        return {"data_extracao": str(data_extracao), "usados": []}
    return est


def escolher(d) -> tuple[str, callable, dict]:
    est = _ler(d.data_extracao)
    usados = set(est["usados"])

    disponiveis = [(k, f) for k, f in catalogo(d) if k not in usados]
    if not disponiveis:  # deu a volta no catálogo antes da extração nova
        est["usados"] = []
        disponiveis = catalogo(d)

    chave, funcao = disponiveis[0]
    est["usados"] = est["usados"] + [chave]
    return chave, funcao, est


def registrar(est: dict) -> None:
    """Só grava DEPOIS que o post foi publicado — senão uma falha de rede queima o corte."""
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(est, indent=2, ensure_ascii=False), encoding="utf-8")
