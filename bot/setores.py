"""Nome amigável -> código de CNAE.

Por que este arquivo existe: a descrição oficial do CNAE **nunca** contém a palavra
que a pessoa usa. Não existe CNAE "barbearia", nem "pizzaria", nem "sorveteria" —
existe "Cabeleireiros, manicure e pedicure" e "Comércio varejista de animais vivos e
de artigos e alimentos para animais de estimação". Buscar por texto livre na descrição
falha exatamente nas palavras que fazem um post ser compartilhado.

Então o mapa é curado, à mão, contra a tabela real de 1.359 CNAEs. É chato e é o
trabalho. Também é o embrião do RF-7 do produto pago ("CNAE com busca por descrição
amigável"), então ele não é jogado fora quando a etapa 2 acabar.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Setor:
    slug: str          # chave estável da agenda — não muda, senão o corte repete
    rotulo: str        # já no plural, porque é assim que entra no texto do post
    codigos: list[str]


SETORES = [
    Setor("padaria", "padarias", ["4721101", "4721102", "1091102"]),
    Setor("salao-de-beleza", "salões de beleza", ["9602501", "9602502"]),
    Setor("petshop", "petshops", ["4789004", "9609208", "9609203"]),
    Setor("academia", "academias", ["9313100"]),
    Setor("lanchonete", "lanchonetes", ["5611203"]),
    Setor("restaurante", "restaurantes", ["5611201"]),
    Setor("bar", "bares", ["5611202", "5611204", "5611205"]),
    Setor("food-truck", "food trucks", ["5612100"]),
    Setor("tatuagem", "estúdios de tatuagem", ["9609206"]),
    Setor("creche", "creches", ["8511200"]),
    Setor("loja-de-roupa", "lojas de roupa", ["4781400"]),
    Setor("psicologia", "consultórios de psicologia", ["8650003"]),
    Setor("cervejaria", "cervejarias", ["1113502"]),
]

POR_SLUG = {s.slug: s for s in SETORES}
