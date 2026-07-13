"""Resolve qual versão do layout usar para uma extração.

Uma extração nova NÃO herda o layout automaticamente: ela cai no layout mais recente
conhecido e o sanity check confere a contagem de colunas. Se a Receita tiver mudado,
o check falha e você adiciona um vNOVO aqui — que é exatamente o comportamento que
se quer, porque a alternativa é o pipeline carregar dado errado em silêncio.
"""

from . import v2026_06

VERSOES = {
    "v2026_06": v2026_06,
}

ATUAL = v2026_06


def para(extracao: str):
    """extracao no formato 'AAAA-MM'."""
    return ATUAL
