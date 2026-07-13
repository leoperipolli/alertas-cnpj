"""Qual corte sai hoje.

Estado num JSON commitado — não precisa de banco. A regra é simples: nunca repetir
um corte enquanto houver corte novo no catálogo, e zerar o catálogo quando chega uma
extração nova (o dado mudou, então os mesmos cortes voltam a ser notícia).
"""

import json
from pathlib import Path

from . import cortes, setores

ESTADO = Path(__file__).resolve().parent.parent / "data" / "agenda_estado.json"


def catalogo(d) -> list[tuple[str, callable]]:
    """~30 posts a partir de 6 cortes. É a parametrização que sustenta a cadência diária."""
    itens: list[tuple[str, callable]] = [
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
