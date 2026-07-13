"""Checks da carga.

O risco desta etapa não é o código quebrar — é o código funcionar e estar errado, e
você postar número errado por 60 dias antes de alguém reparar. Estes checks existem
para tornar isso improvável.

Checks DUROS abortam (o pipeline não pode continuar com dado suspeito). Checks MOLES
imprimem número para você olhar, porque algumas decisões só se toma vendo o dado.
"""

import argparse
import csv
import datetime as dt
import json

from . import config, load, novas
from .layout import ATUAL as layout

# O Brasil abre ~300-400 mil empresas/mês. Numa janela de 90 dias isso é ~0,9-1,2M.
# As bordas são largas de propósito: elas pegam erro de parse (3 mil ou 3 milhões),
# não flutuação de mercado.
MIN_POR_MES = 150_000
MAX_POR_MES = 700_000


class SanityError(RuntimeError):
    pass


def _campos_primeira_linha(caminho) -> int:
    with open(caminho, encoding="latin-1", newline="") as f:
        linha = next(csv.reader(f, delimiter=";", quotechar='"'))
    return len(linha)


def check_carga_completa(extracao: str) -> None:
    """DURO. Carga parcial é o erro mais perigoso do pipeline inteiro.

    A Receita quebra Estabelecimentos em 10 pedaços ARBITRÁRIOS — não por UF, não por
    data. As empresas estão espalhadas aleatoriamente entre eles. Processar 6 de 10 não
    dá "alguns estados": dá ~60% das empresas de todos os estados, e nada na saída
    denuncia isso. O total nacional, a contagem de SP e o ranking inteiro saem
    subestimados em silêncio.

    E o check de ordem de grandeza NÃO pega: 60% de 350 mil ainda cai dentro da faixa
    plausível. Por isso a completude precisa ser verificada aqui, contra o manifest —
    contar linhas depois é tarde demais.
    """
    print("\n[1] Carga completa")
    zips = config.ZIP_DIR / extracao
    manifest_path = zips / "manifest.json"
    if not manifest_path.exists():
        raise SanityError(
            f"sem manifest.json em {zips} — o download nao terminou. "
            f"Rode: python -m etl.download --extracao {extracao}"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    baixados = {a["nome"] for a in manifest["arquivos"]}
    esperados = set(layout.zips_para_baixar())
    if faltando := esperados - baixados:
        raise SanityError(f"CARGA PARCIAL: faltam {sorted(faltando)}")

    for a in manifest["arquivos"]:
        caminho = zips / a["nome"]
        if not caminho.exists():
            raise SanityError(f"{a['nome']} esta no manifest mas sumiu do disco")
        if caminho.stat().st_size != a["bytes"]:
            raise SanityError(
                f"{a['nome']}: {caminho.stat().st_size} bytes em disco, "
                f"{a['bytes']} no manifest — arquivo truncado"
            )
    print(f"    ok  {len(esperados)} zips, {manifest['total_bytes'] / 1e9:.2f} GB, "
          f"tamanhos conferem com o manifest")


def check_colunas(extracao: str) -> None:
    """DURO. Layout mudou -> aborta. É o embrião da quarentena (§7)."""
    print("\n[2] Contagem de colunas por arquivo")
    for tabela, spec in layout.ARQUIVOS.items():
        pasta = config.CSV_DIR / extracao / tabela
        arquivos = sorted(pasta.glob(spec["glob"]))
        # Um zip por CSV: menos CSVs do que zips = extração incompleta.
        if len(arquivos) != len(spec["zips"]):
            raise SanityError(
                f"'{tabela}': {len(arquivos)} CSVs extraidos, {len(spec['zips'])} zips "
                f"esperados. Carga parcial — nao continue."
            )
        esperado = len(spec["colunas"])
        for caminho in arquivos:
            achou = _campos_primeira_linha(caminho)
            if achou != esperado:
                raise SanityError(
                    f"LAYOUT MUDOU: {caminho.name} tem {achou} colunas, o layout "
                    f"'{tabela}' espera {esperado}. Crie um novo etl/layout/vAAAA_MM.py "
                    f"— NAO edite o existente."
                )
        print(f"    ok  {tabela:18} {esperado:2} colunas x {len(arquivos)} arquivo(s)")


def check_privacidade(extracao: str, con, parquet) -> None:
    """DURO. LGPD por construção: dano existencial (§12)."""
    print("\n[3] Privacidade (LGPD)")

    zips = config.ZIP_DIR / extracao
    presentes = {p.name for p in zips.glob("*.zip")}
    vazou = presentes & set(layout.PROIBIDOS)
    if vazou:
        raise SanityError(f"arquivo de Socios em disco: {sorted(vazou)}")
    print(f"    ok  nenhum arquivo de Socios baixado ({len(presentes)} zips em disco)")

    manifest = json.loads((zips / "manifest.json").read_text(encoding="utf-8"))
    nomes = {a["nome"] for a in manifest["arquivos"]}
    if nomes & set(layout.PROIBIDOS):
        raise SanityError("manifest.json registra download de Socios")
    print("    ok  manifest nao registra Socios")

    colunas = [c[0] for c in con.execute(
        f"SELECT * FROM '{parquet.as_posix()}' LIMIT 0"
    ).description]
    fora = set(colunas) - set(novas.ALLOWLIST)
    if fora:
        raise SanityError(f"coluna fora da allowlist LGPD: {sorted(fora)}")
    print(f"    ok  {len(colunas)} colunas, todas na allowlist")

    n_mei_com_endereco = con.execute(f"""
        SELECT count(*) FROM '{parquet.as_posix()}'
        WHERE eh_mei AND endereco IS NOT NULL
    """).fetchone()[0]
    if n_mei_com_endereco:
        raise SanityError(f"{n_mei_com_endereco} MEIs com endereco na saida (§6 item 3)")
    print("    ok  nenhum MEI com endereco")


def check_ordem_de_grandeza(con, parquet, data_ext: dt.date) -> None:
    """DURO. Pega a maioria dos erros de parse sozinho."""
    print("\n[4] Ordem de grandeza")
    n = con.execute(f"SELECT count(*) FROM '{parquet.as_posix()}'").fetchone()[0]
    por_mes = n / (config.JANELA_DIAS / 30)
    print(f"    {n:,} empresas em {config.JANELA_DIAS} dias  =  ~{por_mes:,.0f}/mes")
    if not (MIN_POR_MES <= por_mes <= MAX_POR_MES):
        raise SanityError(
            f"~{por_mes:,.0f} empresas/mes esta fora da faixa plausivel "
            f"({MIN_POR_MES:,}-{MAX_POR_MES:,}). O filtro ou o parse esta errado."
        )
    print(f"    ok  dentro da faixa ({MIN_POR_MES:,}-{MAX_POR_MES:,}/mes)")


def check_reativacao(con, data_ext: dt.date) -> None:
    """DURO. A armadilha que mais provavelmente passaria despercebida."""
    print("\n[5] Armadilha da reativacao")
    inicio = data_ext - dt.timedelta(days=config.JANELA_DIAS)
    n = con.execute(f"""
        SELECT count(*) FROM estabelecimentos
        WHERE situacao_cadastral = '02'
          AND identificador_matriz_filial = '1'
          AND try_strptime(data_situacao_cadastral, '%Y%m%d')::DATE >= DATE '{inicio}'
          AND try_strptime(data_inicio_atividade, '%Y%m%d')::DATE  <  DATE '{inicio}'
    """).fetchone()[0]
    print(f"    {n:,} empresas ATIVAS com situacao recente mas abertura antiga.")
    print("    Sao reativacoes/mudancas de situacao — NAO sao empresas novas.")
    print("    Um filtro ancorado em data_situacao_cadastral incluiria todas elas.")
    print("    ok  filtro ancora em data_inicio_atividade, entao ficam de fora")


def check_uf(con, parquet) -> None:
    """MOLE. SP fora de ~25-35% = join de municipio/uf trocado."""
    print("\n[6] Distribuicao por UF (SP deve ficar perto de ~30%)")
    linhas = con.execute(f"""
        SELECT uf, count(*) AS n,
               100.0 * count(*) / sum(count(*)) OVER () AS pct
        FROM '{parquet.as_posix()}'
        GROUP BY uf ORDER BY n DESC LIMIT 8
    """).fetchall()
    for uf, n, pct in linhas:
        print(f"    {uf}  {n:>8,}  {pct:5.1f}%")
    sp = next((pct for uf, _, pct in linhas if uf == "SP"), 0)
    if not (20 <= sp <= 40):
        print(f"    AVISO: SP em {sp:.1f}% — fora do esperado. Confira o join de UF.")
    else:
        print(f"    ok  SP em {sp:.1f}%")


def check_semanas(con, parquet, data_ext: dt.date) -> None:
    """MOLE. Mostra o efeito da semana parcial — o bot nao pode postar sobre ela."""
    print("\n[7] Aberturas por semana (a ultima e' parcial, cortada pela extracao)")
    linhas = con.execute(f"""
        SELECT date_trunc('week', data_abertura)::DATE AS semana, count(*) AS n
        FROM '{parquet.as_posix()}'
        GROUP BY 1 ORDER BY 1 DESC LIMIT 6
    """).fetchall()
    for semana, n in linhas:
        parcial = (semana + dt.timedelta(days=6)) > data_ext
        marca = "  <- PARCIAL, nao postar" if parcial else ""
        print(f"    {semana}  {n:>8,}{marca}")


def check_matriz_filial(con, data_ext: dt.date) -> None:
    """MOLE. A decisao que o plano deixou para tomar olhando o dado."""
    print("\n[8] Matriz x filial (decisao de escopo)")
    inicio = data_ext - dt.timedelta(days=config.JANELA_DIAS)
    matriz, filial = con.execute(f"""
        SELECT
            count(*) FILTER (WHERE identificador_matriz_filial = '1'),
            count(*) FILTER (WHERE identificador_matriz_filial = '2')
        FROM estabelecimentos
        WHERE situacao_cadastral = '02'
          AND try_strptime(data_inicio_atividade, '%Y%m%d')::DATE
              BETWEEN DATE '{inicio}' AND DATE '{data_ext}'
    """).fetchone()
    meses = config.JANELA_DIAS / 30
    print(f"    matrizes: {matriz:>8,}  (~{matriz / meses:,.0f}/mes)")
    print(f"    filiais:  {filial:>8,}  (~{filial / meses:,.0f}/mes)  = "
          f"{100 * filial / (matriz + filial):.1f}% do total")


def check_spot(con, parquet) -> None:
    """MOLE, mas OBRIGATORIO na primeira carga: o unico teste ponta a ponta real."""
    print("\n[9] Spot-check — confira estes 5 CNPJs num site publico de CNPJ")
    linhas = con.execute(f"""
        SELECT cnpj, razao_social, data_abertura, uf, municipio, cnae_descricao
        FROM '{parquet.as_posix()}'
        WHERE NOT eh_mei
        USING SAMPLE 5 ROWS (reservoir, 42)
    """).fetchall()
    for cnpj, razao, abertura, uf, mun, cnae in linhas:
        fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        print(f"    {fmt}  {abertura}  {(razao or '')[:38]:38} {mun}/{uf}")
        print(f"      {(cnae or '?')[:70]}")
    print("    Devem existir, estar ATIVOS e ter aberto na data acima.")


def verificar(extracao: str, incluir_filiais: bool = False) -> None:
    con, data_ext = load.preparar(extracao)
    parquet = config.OUT_DIR / f"empresas_novas_{extracao}.parquet"
    if not parquet.exists():
        raise SanityError(f"{parquet} nao existe — rode etl.novas primeiro")

    print("=" * 72)
    print(f"SANITY — extracao {extracao} (data oficial da Receita: {data_ext})")
    print("=" * 72)

    check_carga_completa(extracao)
    check_colunas(extracao)
    check_privacidade(extracao, con, parquet)
    check_ordem_de_grandeza(con, parquet, data_ext)
    check_reativacao(con, data_ext)
    check_uf(con, parquet)
    check_semanas(con, parquet, data_ext)
    check_matriz_filial(con, data_ext)
    check_spot(con, parquet)

    print("\n" + "=" * 72)
    print("TODOS OS CHECKS DUROS PASSARAM")
    print("=" * 72)
    con.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--extracao", required=True, help="AAAA-MM")
    p.add_argument("--incluir-filiais", action="store_true")
    args = p.parse_args()
    verificar(args.extracao, args.incluir_filiais)
