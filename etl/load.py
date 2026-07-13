"""Extrai os zips e registra views DuckDB sobre os CSVs.

Tudo é lido como VARCHAR. O cast vem depois, em SQL, porque deixar o DuckDB
adivinhar tipo é como o pipeline passa a carregar lixo em silêncio quando a Receita
muda o layout — e ela muda.
"""

import datetime as dt
import re
import zipfile
from pathlib import Path

from . import config
from .layout import ATUAL as layout


def extrair(extracao: str) -> None:
    """Descompacta os zips em CSV_DIR/<extracao>/<tabela>/."""
    origem = config.ZIP_DIR / extracao
    for tabela, spec in layout.ARQUIVOS.items():
        destino = config.CSV_DIR / extracao / tabela
        destino.mkdir(parents=True, exist_ok=True)
        for nome_zip in spec["zips"]:
            caminho = origem / nome_zip
            with zipfile.ZipFile(caminho) as zf:
                for info in zf.infolist():
                    saida = destino / info.filename
                    if saida.exists() and saida.stat().st_size == info.file_size:
                        continue
                    print(f"  {nome_zip:26} -> {info.filename}", flush=True)
                    zf.extract(info, destino)


def data_extracao(extracao: str) -> dt.date:
    """Lê a data real da extração do nome interno do arquivo.

    A Receita codifica a data no nome (F.K03200$Z.D60613.CNAECSV -> 2026-06-13):
    D + último dígito do ano + MM + DD. É a data que vai em toda mensagem ao
    assinante (RF-3), então ela vem da fonte, não de um palpite sobre a pasta.
    """
    pasta = config.CSV_DIR / extracao / "cnaes"
    arquivos = list(pasta.glob(layout.ARQUIVOS["cnaes"]["glob"]))
    if not arquivos:
        raise RuntimeError(f"nenhum CSV de cnaes em {pasta} — rodou extrair()?")

    m = re.search(r"\.D(\d)(\d{2})(\d{2})\.", arquivos[0].name)
    if not m:
        raise RuntimeError(f"nao achei a data no nome {arquivos[0].name}")

    digito_ano, mes, dia = m.group(1), int(m.group(2)), int(m.group(3))
    ano_pasta = int(extracao[:4])
    # O nome só traz o último dígito do ano; a pasta traz o ano cheio. Se não
    # baterem, a pasta e o conteúdo estão em desacordo e é melhor parar.
    if ano_pasta % 10 != int(digito_ano):
        raise RuntimeError(
            f"ano do arquivo ({digito_ano}) nao bate com a pasta ({ano_pasta})"
        )

    data = dt.date(ano_pasta, mes, dia)
    if data.strftime("%Y-%m") != extracao:
        raise RuntimeError(f"data {data} fora do mes da extracao {extracao}")
    return data


def _colunas_sql(colunas: list[str]) -> str:
    return ", ".join(f"'{c}': 'VARCHAR'" for c in colunas)


def criar_views(con, extracao: str) -> None:
    """Registra uma view por tabela do layout, todas as colunas como VARCHAR."""
    opts = layout.CSV_OPTS
    for tabela, spec in layout.ARQUIVOS.items():
        padrao = (config.CSV_DIR / extracao / tabela / spec["glob"]).as_posix()
        con.execute(f"""
            CREATE OR REPLACE VIEW {tabela} AS
            SELECT * FROM read_csv(
                '{padrao}',
                columns = {{{_colunas_sql(spec["colunas"])}}},
                delim = '{opts["delim"]}',
                header = {str(opts["header"]).lower()},
                quote = '{opts["quote"]}',
                encoding = '{opts["encoding"]}',
                ignore_errors = false
            )
        """)


def preparar(extracao: str):
    """Extrai, abre a conexão e registra as views. Devolve (con, data_extracao)."""
    config.ensure_dirs()
    extrair(extracao)
    con = config.duckdb_connect()
    criar_views(con, extracao)
    return con, data_extracao(extracao)
