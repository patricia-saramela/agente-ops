"""Avisa o Bing (e os outros buscadores do IndexNow) sobre páginas novas ou alteradas.

Rode DEPOIS do deploy na Vercel, quando as páginas já estiverem no ar.

    python scripts/indexnow.py                 # envia todas as URLs do sitemap.xml
    python scripts/indexnow.py --since HEAD~1  # só as páginas .html alteradas desde esse commit
    python scripts/indexnow.py componente-modals.html index.html
    python scripts/indexnow.py --dry-run       # mostra o que seria enviado, sem enviar

A chave fica no arquivo <KEY>.txt na raiz do site; ele precisa estar publicado
em https://agente-ops.vercel.app/<KEY>.txt para o IndexNow aceitar o envio.
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOST = "agente-ops.vercel.app"
BASE = f"https://{HOST}/"
KEY = "7ff4c1045c4c1115b026a219adc1897e"
ENDPOINT = "https://api.indexnow.org/indexnow"
ROOT = Path(__file__).resolve().parent.parent


def url_for(page: str) -> str:
    page = page.replace("\\", "/").lstrip("/")
    return BASE if page in ("", "index.html") else BASE + page


def sitemap_urls() -> list[str]:
    xml = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def changed_pages(ref: str) -> list[str]:
    out = subprocess.run(
        ["git", "diff", "--name-only", ref, "--", "*.html"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout
    return [p for p in out.split() if (ROOT / p).exists()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pages", nargs="*", help="arquivos .html a enviar (padrão: todo o sitemap)")
    ap.add_argument("--since", metavar="REF", help="enviar só as páginas alteradas desde este commit")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.since:
        urls = [url_for(p) for p in changed_pages(args.since)]
    elif args.pages:
        urls = [url_for(p) for p in args.pages]
    else:
        urls = sitemap_urls()

    if not urls:
        print("Nenhuma URL para enviar.")
        return 0

    payload = {"host": HOST, "key": KEY, "keyLocation": f"{BASE}{KEY}.txt", "urlList": urls}
    print(f"{len(urls)} URL(s):", *urls, sep="\n  ")
    if args.dry_run:
        return 0

    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"IndexNow respondeu {resp.status} (200 ou 202 = recebido).")
            return 0
    except urllib.error.HTTPError as e:
        motivos = {400: "pedido inválido", 403: "chave não encontrada no site (o .txt está publicado?)",
                   422: "URLs não pertencem ao host", 429: "muitos envios; tente mais tarde"}
        print(f"IndexNow respondeu {e.code}: {motivos.get(e.code, e.reason)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
