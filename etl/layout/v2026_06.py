"""Layout dos Dados Abertos CNPJ — versão observada na extração 2026-06.

A Receita muda este layout sem aviso (a última vez foi em jan/2026). Quando mudar,
crie um NOVO arquivo aqui (v2026_11.py, ...) em vez de editar este. O diretório é a
resposta estrutural ao RNF-8: a quebra anual vira "adicionar um arquivo", não
"arqueologia no parser".

Os CSVs não têm cabeçalho — a ORDEM das colunas abaixo é o contrato. Se a Receita
inserir uma coluna no meio, todas as seguintes viram lixo silenciosamente. Por isso
`etl/sanity.py` confere a contagem de colunas antes de qualquer carga.
"""

# Os arquivos dentro dos zips têm nomes internos crípticos (ex.: K3241.K03200Y0.D60614.EMPRECSV),
# então a extração acha o CSV pelo sufixo, não pelo nome.
ARQUIVOS = {
    "empresas": {
        "zips": [f"Empresas{i}.zip" for i in range(10)],
        "glob": "*.EMPRECSV",
        "colunas": [
            "cnpj_basico",
            "razao_social",
            "natureza_juridica",
            "qualificacao_responsavel",
            "capital_social",
            "porte",
            "ente_federativo_responsavel",
        ],
    },
    "estabelecimentos": {
        "zips": [f"Estabelecimentos{i}.zip" for i in range(10)],
        "glob": "*.ESTABELE",
        "colunas": [
            "cnpj_basico",
            "cnpj_ordem",
            "cnpj_dv",
            "identificador_matriz_filial",
            "nome_fantasia",
            "situacao_cadastral",
            "data_situacao_cadastral",
            "motivo_situacao_cadastral",
            "nome_cidade_exterior",
            "pais",
            "data_inicio_atividade",
            "cnae_fiscal_principal",
            "cnae_fiscal_secundaria",
            "tipo_logradouro",
            "logradouro",
            "numero",
            "complemento",
            "bairro",
            "cep",
            "uf",
            "municipio",
            "ddd_1",
            "telefone_1",
            "ddd_2",
            "telefone_2",
            "ddd_fax",
            "fax",
            "correio_eletronico",
            "situacao_especial",
            "data_situacao_especial",
        ],
    },
    "simples": {
        "zips": ["Simples.zip"],
        "glob": "*.SIMPLES*",
        "colunas": [
            "cnpj_basico",
            "opcao_simples",
            "data_opcao_simples",
            "data_exclusao_simples",
            "opcao_mei",
            "data_opcao_mei",
            "data_exclusao_mei",
        ],
    },
    "cnaes": {
        "zips": ["Cnaes.zip"],
        "glob": "*.CNAECSV",
        "colunas": ["codigo", "descricao"],
    },
    "municipios": {
        "zips": ["Municipios.zip"],
        "glob": "*.MUNICCSV",
        # ATENÇÃO: este é o código de município DA RECEITA, não o do IBGE.
        # Juntar com dado do IBGE sem uma tabela de-para produz município errado.
        "colunas": ["codigo", "descricao"],
    },
    "naturezas": {
        "zips": ["Naturezas.zip"],
        "glob": "*.NATJUCSV",
        "colunas": ["codigo", "descricao"],
    },
}

# Os arquivos de Sócios existem na origem e são deliberadamente omitidos daqui.
# Isto é uma allowlist, não uma blocklist: nada é baixado a menos que esteja em ARQUIVOS.
# Não dá para vazar o que nunca se teve (RF-1, §6 do documento de desenvolvimento).
PROIBIDOS = ["Socios0.zip", "Socios1.zip", "Socios2.zip", "Socios3.zip", "Socios4.zip",
             "Socios5.zip", "Socios6.zip", "Socios7.zip", "Socios8.zip", "Socios9.zip"]

CSV_OPTS = {
    "delim": ";",
    "header": False,
    "quote": '"',
    "encoding": "latin-1",
}


def zips_para_baixar() -> list[str]:
    nomes = [z for spec in ARQUIVOS.values() for z in spec["zips"]]
    proibidos = set(PROIBIDOS)
    assert not (set(nomes) & proibidos), "arquivo de Sócios entrou na allowlist"
    return nomes
