#!/usr/bin/env python3
"""Render index.html from publications.bib.

Usage: python3 build.py
Entries whose key starts with figshare_/zenodo_ are listed as talks & media;
everything else as papers.
"""
import html
import re
from pathlib import Path

ROOT = Path(__file__).parent
TALK_PREFIXES = ("figshare_", "zenodo_")
ME = "Montanari"


def parse_bib(text):
    entries = []
    for chunk in re.split(r"\n(?=@)", text.strip()):
        chunk = chunk.strip()
        m = re.match(r"@(\w+)\{([^,]+),", chunk)
        if not m:
            continue
        fields = {}
        for fm in re.finditer(r"(\w+)\s*=\s*\{((?:[^{}]|\{[^{}]*\})*)\}", chunk):
            fields[fm.group(1).lower()] = re.sub(r"\s+", " ", fm.group(2)).strip()
        entries.append({"type": m.group(1).lower(), "key": m.group(2), "fields": fields, "raw": chunk})
    return entries


def clean(s):
    s = s.replace("{", "").replace("}", "").replace("---", "—").replace("--", "–")
    return s.replace("\\&", "&")


def authors(f):
    out = []
    for a in f.get("author", "").split(" and "):
        a = clean(a)
        if "," in a:
            last, first = [x.strip() for x in a.split(",", 1)]
        else:
            parts = a.split()
            last, first = parts[-1], " ".join(parts[:-1])
        initials = " ".join(p[0] + "." for p in re.split(r"[\s-]+", first) if p)
        out.append((last, initials))
    return out


def fmt_authors_html(f):
    names = []
    for last, ini in authors(f):
        n = html.escape(f"{last}, {ini}".strip(", "))
        names.append(f"<strong>{n}</strong>" if last == ME else n)
    return ", ".join(names)


def fmt_authors_text(f):
    return ", ".join(f"{last}, {ini}".strip(", ") for last, ini in authors(f))


def venue(f):
    return clean(f.get("journal") or f.get("booktitle") or f.get("publisher") or "")


def title(f):
    t = clean(f.get("title", ""))
    return t[:1] + t[1:].lower() if t.isupper() else t


def doi(f):
    d = f.get("doi", "")
    return d.lower() if d.lower().startswith("10.") else d


def plain_citation(e):
    f = e["fields"]
    s = f"{fmt_authors_text(f)} ({f.get('year', 'n.d.')}). {title(f)}. {venue(f)}."
    if doi(f):
        s += f" https://doi.org/{doi(f)}"
    elif f.get("url"):
        s += f" {f['url']}"
    return s


def render_entry(e):
    f = e["fields"]
    d = doi(f)
    link = f"https://doi.org/{d}" if d else f.get("url", "")
    links = []
    if link:
        label = f"doi:{d}" if d else "link"
        links.append(f'<a href="{html.escape(link)}" rel="noopener">{html.escape(label)}</a>')
    bib_id = "bib-" + re.sub(r"[^A-Za-z0-9_-]", "-", e["key"])
    return f"""
      <li class="pub" data-year="{html.escape(f.get('year', ''))}">
        <div class="pub-year">{html.escape(f.get('year', ''))}</div>
        <div class="pub-body">
          <p class="pub-title">{html.escape(title(f))}</p>
          <p class="pub-meta">{fmt_authors_html(f)}<span class="sep"> · </span><em>{html.escape(venue(f))}</em></p>
          <div class="pub-actions">
            {''.join(links)}
            <button type="button" class="chip" data-toggle="{bib_id}" aria-expanded="false">BibTeX</button>
            <button type="button" class="chip" data-copy-text="{html.escape(plain_citation(e))}">Copy citation</button>
          </div>
          <div class="bib" id="{bib_id}" hidden>
            <pre><code>{html.escape(e['raw'])}</code></pre>
            <button type="button" class="chip copy-bib" data-copy-from="{bib_id}">Copy BibTeX</button>
          </div>
        </div>
      </li>"""


def main():
    bib_text = (ROOT / "publications.bib").read_text(encoding="utf-8")
    entries = parse_bib(bib_text)
    year = lambda e: int(e["fields"].get("year", "0") or 0)
    papers = sorted([e for e in entries if not e["key"].startswith(TALK_PREFIXES)], key=year, reverse=True)
    talks = sorted([e for e in entries if e["key"].startswith(TALK_PREFIXES)], key=year, reverse=True)
    tpl = (ROOT / "template.html").read_text(encoding="utf-8")
    out = (tpl.replace("{{PAPERS}}", "".join(render_entry(e) for e in papers))
              .replace("{{TALKS}}", "".join(render_entry(e) for e in talks))
              .replace("{{N_PAPERS}}", str(len(papers)))
              .replace("{{N_TALKS}}", str(len(talks)))
              .replace("{{ALL_BIB}}", html.escape(bib_text.strip())))
    (ROOT / "index.html").write_text(out, encoding="utf-8")
    print(f"index.html: {len(papers)} papers, {len(talks)} talks/media")


if __name__ == "__main__":
    main()
