"""Caminhos e parâmetros do pipeline.

Os dados brutos NÃO podem morar dentro do repositório: a pasta do projeto está no
OneDrive, e 20 GB de CSV fariam o OneDrive sincronizar tudo para a nuvem.
"""

import os
from pathlib import Path

DATA_DIR = Path(os.environ.get("CNPJ_DATA_DIR", r"C:\cnpj-data"))

ZIP_DIR = DATA_DIR / "zips"
CSV_DIR = DATA_DIR / "csv"
TMP_DIR = DATA_DIR / "tmp"
OUT_DIR = DATA_DIR / "out"

REPO_DIR = Path(__file__).resolve().parent.parent
AGREGADOS_PARQUET = REPO_DIR / "data" / "agregados.parquet"

BASE_URL = "https://arquivos.receitafederal.gov.br/public.php/webdav"
SHARE_TOKEN = "YggdBLfdninEJX9"

# Com 8 GB de RAM (e ~1,5 GB livres), o DuckDB precisa derramar para o disco.
# Isso é esperado, não é erro: ele processa fora da memória lendo do CSV.
DUCKDB_MEMORY_LIMIT = "3GB"

JANELA_DIAS = 90


def duckdb_connect():
    import duckdb

    con = duckdb.connect()
    con.execute(f"SET memory_limit = '{DUCKDB_MEMORY_LIMIT}'")
    con.execute(f"SET temp_directory = '{TMP_DIR.as_posix()}'")
    con.execute("SET preserve_insertion_order = false")
    return con


def ensure_dirs():
    for d in (ZIP_DIR, CSV_DIR, TMP_DIR, OUT_DIR, AGREGADOS_PARQUET.parent):
        d.mkdir(parents=True, exist_ok=True)
