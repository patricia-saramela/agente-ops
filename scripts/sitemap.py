"""Gera o sitemap.xml com a data real de alteração de cada página.

O Bing usa o <lastmod> para decidir o que rastrear de novo, e pede que ele
mude só quando o conteúdo da página mudou. Por isso a data vem do Git:
  - página com alterações ainda não commitadas: data de hoje;
  - página sem alterações: data do último commit que a modificou.

Rode antes de cada commit que altera páginas:

    python scripts/sitemap.py
"""
import datetime
import subprocess
from pathlib import Path

BASE = "https://agente-ops.vercel.app/"
ROOT = Path(__file__).resolve().parent.parent
# ordem do sitemap: índice, partes gerais, componentes, suporte
FIRST = ["index.html", "fundamentos.html", "variaveis-da-marca.html",
         "respostas-rapidas.html", "da-para-fazer.html"]
LAST = ["suporte-guias-e-duvidas.html", "bugs-conhecidos.html"]


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                          text=True, check=True).stdout.strip()


def lastmod(page: str, dirty: set[str]) -> str:
    if page in dirty:
        return datetime.date.today().isoformat()
    return git("log", "-1", "--format=%cs", "--", page) or datetime.date.today().isoformat()


def main() -> None:
    dirty = {line[3:].strip() for line in git("status", "--porcelain", "--", "*.html").splitlines()}
    pages = sorted(p.name for p in ROOT.glob("*.html"))
    comps = [p for p in pages if p.startswith("componente-")]
    others = [p for p in pages if p not in comps and p not in FIRST and p not in LAST]
    ordered = [p for p in FIRST if p in pages] + comps + others + [p for p in LAST if p in pages]

    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p in ordered:
        loc = BASE if p == "index.html" else BASE + p
        lines += ["  <url>", f"    <loc>{loc}</loc>", f"    <lastmod>{lastmod(p, dirty)}</lastmod>", "  </url>"]
    lines.append("</urlset>")
    (ROOT / "sitemap.xml").write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    print(f"sitemap.xml: {len(ordered)} URLs")


if __name__ == "__main__":
    main()
