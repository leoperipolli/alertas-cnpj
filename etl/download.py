"""Baixa os zips de uma extração dos Dados Abertos CNPJ.

Fonte: Nextcloud público da Receita. Autenticação = token do share como usuário,
senha vazia. O endpoint aceita Range, então o download é resumível — o que importa
porque são ~6,4 GB e a conexão cai.

Só baixa o que está na allowlist do layout. Sócios nunca entra (LGPD por construção).
"""

import argparse
import hashlib
import json
import sys
import time
import zipfile
from pathlib import Path

import requests

from . import config
from .layout import ATUAL as layout

CHUNK = 1 << 20  # 1 MiB
TENTATIVAS = 8   # por arquivo; cada uma retoma de onde parou


def _url(extracao: str, nome: str) -> str:
    return f"{config.BASE_URL}/{extracao}/{nome}"


def _sessao() -> requests.Session:
    s = requests.Session()
    s.auth = (config.SHARE_TOKEN, "")
    return s


def tamanho_remoto(sessao: requests.Session, url: str) -> int:
    r = sessao.head(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return int(r.headers["Content-Length"])


def _um_trecho(sessao: requests.Session, url: str, destino: Path,
               ja_tem: int, total: int) -> int:
    """Baixa de `ja_tem` até o fim. Devolve quantos bytes há no arquivo ao terminar."""
    headers = {"Range": f"bytes={ja_tem}-"} if ja_tem else {}
    modo = "ab" if ja_tem else "wb"

    with sessao.get(url, headers=headers, stream=True, timeout=120) as r:
        r.raise_for_status()
        baixado = ja_tem
        with open(destino, modo) as f:
            for chunk in r.iter_content(CHUNK):
                f.write(chunk)
                baixado += len(chunk)
                pct = 100 * baixado / total
                print(f"\r    {pct:5.1f}%  {baixado / 1e6:7.0f}/{total / 1e6:.0f} MB",
                      end="", flush=True)
        print()
    return baixado


def baixar_um(sessao: requests.Session, extracao: str, nome: str, destino: Path) -> dict:
    url = _url(extracao, nome)
    total = tamanho_remoto(sessao, url)
    destino.parent.mkdir(parents=True, exist_ok=True)

    ja_tem = destino.stat().st_size if destino.exists() else 0
    if ja_tem == total:
        print(f"  {nome:26} ja completo ({total / 1e6:.0f} MB)")
    else:
        if ja_tem > total:  # arquivo corrompido de uma execução anterior
            destino.unlink()
            ja_tem = 0

        rotulo = "retomando" if ja_tem else "baixando"
        print(f"  {nome:26} {rotulo} ({total / 1e6:.0f} MB)", flush=True)

        # O servidor da Receita derruba a conexão no meio de arquivo grande — não é
        # exceção, é rotina. Sem retry, uma queda mata uma execução de horas e exige
        # alguém reinvocar na mão; isso não sobrevive a rodar sozinho todo mês.
        # Cada tentativa retoma do byte onde parou, então nada é rebaixado.
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                ja_tem = _um_trecho(sessao, url, destino, ja_tem, total)
                break
            except (requests.RequestException, ConnectionError, OSError) as e:
                ja_tem = destino.stat().st_size if destino.exists() else 0
                if tentativa == TENTATIVAS:
                    raise RuntimeError(
                        f"{nome}: {TENTATIVAS} tentativas falharam, "
                        f"parou em {ja_tem / 1e6:.0f}/{total / 1e6:.0f} MB"
                    ) from e
                espera = min(2 ** tentativa, 60)
                print(f"\n    conexao caiu ({type(e).__name__}) em "
                      f"{ja_tem / 1e6:.0f} MB — retomando em {espera}s "
                      f"[{tentativa}/{TENTATIVAS}]", flush=True)
                time.sleep(espera)

    final = destino.stat().st_size
    if final != total:
        raise RuntimeError(f"{nome}: baixou {final} bytes, esperava {total}")

    # Um zip truncado ou corrompido só aparece na hora de extrair, horas depois.
    # Testar aqui custa segundos e evita reprocessar a extração inteira.
    if not zipfile.is_zipfile(destino):
        destino.unlink()
        raise RuntimeError(f"{nome}: nao e um zip valido (removido, rode de novo)")

    h = hashlib.sha256()
    with open(destino, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK), b""):
            h.update(chunk)

    return {"nome": nome, "bytes": total, "sha256": h.hexdigest()}


def baixar(extracao: str) -> dict:
    config.ensure_dirs()
    sessao = _sessao()
    alvo = config.ZIP_DIR / extracao

    nomes = layout.zips_para_baixar()
    print(f"Extracao {extracao}: {len(nomes)} arquivos (Socios NAO entra na lista)\n")

    arquivos = [baixar_um(sessao, extracao, nome, alvo / nome) for nome in nomes]

    baixados = {p.name for p in alvo.glob("*.zip")}
    vazou = baixados & set(layout.PROIBIDOS)
    if vazou:
        raise RuntimeError(f"arquivo proibido presente em {alvo}: {sorted(vazou)}")

    manifest = {
        "extracao": extracao,
        "base_url": config.BASE_URL,
        "arquivos": arquivos,
        "total_bytes": sum(a["bytes"] for a in arquivos),
    }
    caminho = alvo / "manifest.json"
    caminho.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nOK: {manifest['total_bytes'] / 1e9:.2f} GB -> {alvo}")
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--extracao", required=True, help="AAAA-MM, ex: 2026-06")
    args = p.parse_args()
    try:
        baixar(args.extracao)
    except Exception as e:
        print(f"\nFALHOU: {e}", file=sys.stderr)
        sys.exit(1)
