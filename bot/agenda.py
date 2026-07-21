"""Qual corte sai agora.

Estado num JSON commitado — não precisa de banco. A regra é simples: nunca repetir
um corte enquanto houver corte novo na fila, e zerar tudo quando chega uma extração
nova (o dado mudou, então os mesmos cortes voltam a ser notícia).

São DUAS filas, sorteadas em horários diferentes do dia:

- `novo`     — os contraintuitivos (per capita, razões, location quotient). Sai de manhã.
- `classico` — placar, rankings, setores, duelos. Sai à noite.

Duas filas em vez de uma só porque o dia tem dois posts e eles não podem ser do mesmo
tipo: dois rankings seguidos cansam, e dois "vira a mesa" seguidos gastam o que o
perfil tem de melhor no dobro da velocidade. Cada fila se esgota e zera por conta
própria.
"""

import json
from pathlib import Path

from . import cortes, setores

ESTADO = Path(__file__).resolve().parent.parent / "data" / "agenda_estado.json"


def contraintuitivos(d) -> list[tuple[str, callable]]:
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

        # --- daqui para baixo, a fila que sustenta o mês inteiro a 1 por dia ---
        # Só setores com volume nacional que aguenta ranking por habitante. Creche (51
        # aberturas em junho), cervejaria (7) e tatuagem (528) ficam DE FORA: com N
        # baixo o líder per capita muda por acaso e o post vira ruído.
        ("percapita|loja-de-roupa",
         lambda saida: cortes.ranking_per_capita(d, saida, "loja-de-roupa", piso=60)),
        ("percapita|lanchonete",
         lambda saida: cortes.ranking_per_capita(d, saida, "lanchonete", piso=40)),
        ("percapita|padaria",
         lambda saida: cortes.ranking_per_capita(d, saida, "padaria", piso=35)),
        ("percapita|food-truck",
         lambda saida: cortes.ranking_per_capita(d, saida, "food-truck", piso=30)),
        ("percapita|petshop",
         lambda saida: cortes.ranking_per_capita(d, saida, "petshop", piso=25)),
        ("percapita|psicologia",
         lambda saida: cortes.ranking_per_capita(d, saida, "psicologia", piso=25)),

        ("razao|lanchonete-restaurante", lambda saida: cortes.razao_setores(
            d, saida, "lanchonete-restaurante",
            "Lanchonetes por restaurante",
            "Quantas lanchonetes novas abrem para cada restaurante novo em {mes}",
            ["lanchonete"], ["restaurante"],
            "Em {lider}, abrem {r} lanchonetes para cada restaurante.",
            "Seu estado come em pé ou sentado?", piso_den=40)),
        ("razao|foodtruck-restaurante", lambda saida: cortes.razao_setores(
            d, saida, "foodtruck-restaurante",
            "Food trucks por restaurante",
            "Quantos food trucks novos abrem para cada restaurante novo em {mes}",
            ["food-truck"], ["restaurante"],
            "Em {lider}, abrem {r} food trucks para cada restaurante.",
            "A rua está ganhando do salão?", piso_den=40)),
        ("razao|roupa-salao", lambda saida: cortes.razao_setores(
            d, saida, "roupa-salao",
            "Lojas de roupa por salão de beleza",
            "Quantas lojas de roupa novas abrem para cada salão novo em {mes}",
            ["loja-de-roupa"], ["salao-de-beleza"],
            "Em {lider}, abrem {r} lojas de roupa para cada salão de beleza.",
            "Vestir ou cuidar: o que seu estado escolhe?", piso_den=60)),

        # O líder de cada um é DESCOBERTO na hora (ver cortes.lq_hero), então estes
        # continuam corretos quando a extração mudar quem lidera.
        ("lqhero|representante", lambda saida: cortes.lq_hero(
            d, saida, "representante", ["4619200"], "representante comercial")),
        ("lqhero|maquina-agricola", lambda saida: cortes.lq_hero(
            d, saida, "maquina-agricola", ["3314711"], "manutenção de máquina agrícola")),
        ("lqhero|faccao", lambda saida: cortes.lq_hero(
            d, saida, "faccao", ["1412603"], "facção de roupa")),
        ("lqhero|calcados", lambda saida: cortes.lq_hero(
            d, saida, "calcados", ["1531902"], "acabamento de calçados")),
        ("lqhero|colheita", lambda saida: cortes.lq_hero(
            d, saida, "colheita", ["0161003"], "serviço de colheita")),

        # Pares sem relação nenhuma: a correlação existe e a causa é boba (o tamanho
        # do estado). Contagem bruta de propósito — normalizar mataria a piada.
        ("espuria|petshop-lanchonete", lambda saida: cortes.correlacao_espuria(
            d, saida, "petshop-lanchonete", "petshop", "lanchonete")),
        ("espuria|salao-foodtruck", lambda saida: cortes.correlacao_espuria(
            d, saida, "salao-foodtruck", "salao-de-beleza", "food-truck")),
        ("espuria|roupa-restaurante", lambda saida: cortes.correlacao_espuria(
            d, saida, "roupa-restaurante", "loja-de-roupa", "restaurante")),
    ]


def classicos(d) -> list[tuple[str, callable]]:
    """Placar, rankings, setores e duelos — o corte honesto e direto, sem a virada."""
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


FILAS = {"novo": contraintuitivos, "classico": classicos}


def catalogo(d) -> list[tuple[str, callable]]:
    """As duas filas juntas — usado por `run.py --todos` e pela revisão da fila."""
    return [*contraintuitivos(d), *classicos(d)]


def _ler(data_extracao) -> dict:
    vazio = {"data_extracao": str(data_extracao), "usados": {k: [] for k in FILAS}}
    if not ESTADO.exists():
        return vazio
    est = json.loads(ESTADO.read_text(encoding="utf-8"))
    if est.get("data_extracao") != str(data_extracao):
        return vazio  # extração nova: as duas filas voltam a valer inteiras
    # O formato antigo guardava uma lista única (uma fila só, um post por dia).
    if not isinstance(est.get("usados"), dict):
        return vazio
    for nome in FILAS:
        est["usados"].setdefault(nome, [])
    return est


def escolher(d, fila: str = "novo") -> tuple[str, callable, dict]:
    if fila not in FILAS:
        raise ValueError(f"fila desconhecida: {fila!r} (use {sorted(FILAS)})")

    est = _ler(d.data_extracao)
    usados = set(est["usados"][fila])

    disponiveis = [(k, f) for k, f in FILAS[fila](d) if k not in usados]
    if not disponiveis:  # deu a volta nesta fila antes da extração nova
        est["usados"][fila] = []
        disponiveis = FILAS[fila](d)

    chave, funcao = disponiveis[0]
    est["usados"][fila] = est["usados"][fila] + [chave]
    return chave, funcao, est


def registrar(est: dict) -> None:
    """Só grava DEPOIS que o post foi publicado — senão uma falha de rede queima o corte."""
    ESTADO.parent.mkdir(parents=True, exist_ok=True)
    ESTADO.write_text(json.dumps(est, indent=2, ensure_ascii=False), encoding="utf-8")
