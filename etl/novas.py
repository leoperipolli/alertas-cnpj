"""Filtra as empresas recém-abertas e ativas da extração.

Este é o núcleo de correção do produto inteiro. Duas coisas nele não são negociáveis:

1. O filtro ancora em `data_inicio_atividade`, NUNCA em `data_situacao_cadastral`.
   Uma empresa suspensa que voltou à ativa tem situação recente e abertura antiga —
   ela não é nova. Um contador que receber empresa de 2019 numa lista de "abriram
   essa semana" cancela na hora.

2. As colunas são nomeadas uma a uma (allowlist LGPD, §6). Nunca `SELECT *`. Coluna
   nova que a Receita inventar fica invisível até alguém decidir incluí-la, com a
   pergunta de auditoria: "essa coluna identifica pessoa? Corta."
"""

import argparse
import datetime as dt

from . import config, load

# A saída tem exatamente estas colunas. `etl/sanity.py` falha se aparecer outra.
ALLOWLIST = [
    "cnpj",
    "razao_social",
    "nome_fantasia",
    "cnae_principal",
    "cnae_descricao",
    "cnaes_secundarios",
    "data_abertura",
    "data_situacao",
    "natureza_juridica",
    "natureza_descricao",
    "porte",
    "capital_social",
    "municipio_codigo",
    "municipio",
    "uf",
    "endereco",
    "eh_mei",
]


def sql(data_ext: dt.date, incluir_filiais: bool) -> str:
    inicio = data_ext - dt.timedelta(days=config.JANELA_DIAS)
    filtro_matriz = "" if incluir_filiais else "AND identificador_matriz_filial = '1'"

    return f"""
    WITH est AS (
        -- Filtrar ANTES de qualquer join: derruba ~60M linhas para ~1M e é o que
        -- permite isto rodar em 3 GB de RAM.
        SELECT
            cnpj_basico,
            cnpj_ordem,
            cnpj_dv,
            nome_fantasia,
            cnae_fiscal_principal,
            cnae_fiscal_secundaria,
            try_strptime(data_inicio_atividade, '%Y%m%d')::DATE   AS data_abertura,
            try_strptime(data_situacao_cadastral, '%Y%m%d')::DATE AS data_situacao,
            municipio,
            uf,
            nullif(trim(concat_ws(' ',
                nullif(tipo_logradouro, ''), nullif(logradouro, ''),
                nullif(numero, ''), nullif(complemento, ''),
                nullif(bairro, ''), nullif(cep, '')
            )), '') AS endereco_bruto
        FROM estabelecimentos
        WHERE situacao_cadastral = '02'                        -- ativa
          AND try_strptime(data_inicio_atividade, '%Y%m%d')::DATE
              BETWEEN DATE '{inicio}' AND DATE '{data_ext}'    -- recém-aberta
          {filtro_matriz}
    ),
    mei AS (
        SELECT cnpj_basico FROM simples WHERE opcao_mei = 'S'
    )
    SELECT
        est.cnpj_basico || est.cnpj_ordem || est.cnpj_dv        AS cnpj,
        emp.razao_social                                        AS razao_social,
        nullif(est.nome_fantasia, '')                           AS nome_fantasia,
        est.cnae_fiscal_principal                               AS cnae_principal,
        cna.descricao                                           AS cnae_descricao,
        nullif(est.cnae_fiscal_secundaria, '')                  AS cnaes_secundarios,
        est.data_abertura                                       AS data_abertura,
        est.data_situacao                                       AS data_situacao,
        emp.natureza_juridica                                   AS natureza_juridica,
        nat.descricao                                           AS natureza_descricao,
        CASE
            WHEN mei.cnpj_basico IS NOT NULL THEN 'MEI'
            WHEN emp.porte = '01' THEN 'ME'
            WHEN emp.porte = '03' THEN 'EPP'
            WHEN emp.porte = '05' THEN 'demais'
        END                                                     AS porte,
        try_cast(replace(emp.capital_social, ',', '.') AS DECIMAL(15,2))
                                                                AS capital_social,
        est.municipio                                           AS municipio_codigo,
        mun.descricao                                           AS municipio,
        est.uf                                                  AS uf,
        -- MEI é pessoa física: o endereço dele é o endereço residencial dele.
        -- A linha entra (filtrar por porte MEI é caso de uso legítimo do contador),
        -- mas sem endereço. §6, item 3.
        CASE WHEN mei.cnpj_basico IS NULL THEN est.endereco_bruto END AS endereco,
        mei.cnpj_basico IS NOT NULL                             AS eh_mei
    FROM est
    JOIN empresas   emp ON emp.cnpj_basico = est.cnpj_basico
    LEFT JOIN mei          ON mei.cnpj_basico = est.cnpj_basico
    LEFT JOIN cnaes      cna ON cna.codigo = est.cnae_fiscal_principal
    LEFT JOIN municipios mun ON mun.codigo = est.municipio
    LEFT JOIN naturezas  nat ON nat.codigo = emp.natureza_juridica
    """


def gerar(extracao: str, incluir_filiais: bool = False):
    con, data_ext = load.preparar(extracao)
    print(f"Extracao {extracao} — data oficial da Receita: {data_ext}")
    print(f"Janela: {config.JANELA_DIAS} dias  |  filiais: {'sim' if incluir_filiais else 'nao'}")

    destino = config.OUT_DIR / f"empresas_novas_{extracao}.parquet"
    con.execute(f"""
        COPY ({sql(data_ext, incluir_filiais)})
        TO '{destino.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)

    n = con.execute(f"SELECT count(*) FROM '{destino.as_posix()}'").fetchone()[0]
    print(f"\n{n:,} empresas novas -> {destino}")
    return con, data_ext, destino


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--extracao", required=True, help="AAAA-MM")
    p.add_argument("--incluir-filiais", action="store_true")
    args = p.parse_args()
    gerar(args.extracao, args.incluir_filiais)
