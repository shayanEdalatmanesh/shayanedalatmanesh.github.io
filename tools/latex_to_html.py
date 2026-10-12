#!/usr/bin/env python3
"""
Convert a LaTeX publication list into HTML and insert it into publications.html.

Usage:
    python3 tools/latex_to_html.py mypubs.tex
    python3 tools/latex_to_html.py mypubs.tex --html path/to/publications.html

Input: a .tex file (or just the snippet) where each paper is a \\item or \\bibitem,
or, failing that, a paragraph separated by blank lines. Order is preserved, so keep it
reverse chronological. \\underline{...} (your name) is rendered underlined.

Supported: \\underline \\textbf \\textit \\emph \\href \\url \\doi, {\\bf ..} {\\it ..} {\\em ..},
accents (\\"o \\'e \\v{c} ...), \\&, ~, --, ---, simple math sub/superscripts like Cu$_2$O.
Entries are grouped by year (the last 4-digit year found in each entry).

The script rewrites everything between <!-- PUBS:START --> and <!-- PUBS:END -->.
"""
import argparse
import html
import re
import sys
import unicodedata
from pathlib import Path

ACCENTS = {
    "'": "\u0301", "`": "\u0300", '"': "\u0308", "^": "\u0302", "~": "\u0303",
    ".": "\u0307", "=": "\u0304",
    "v": "\u030c", "c": "\u0327", "u": "\u0306", "H": "\u030b", "r": "\u030a",
}
LETTER_SPECIALS = {
    "ss": "ß", "o": "ø", "O": "Ø", "aa": "å", "AA": "Å", "ae": "æ", "AE": "Æ",
    "oe": "œ", "OE": "Œ", "l": "ł", "L": "Ł", "i": "i", "j": "j",
    "textendash": "–", "textemdash": "—", "textquoteright": "’", "textquoteleft": "‘",
    "textdegree": "°", "textmu": "µ", "angstrom": "Å",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "theta": "θ",
    "lambda": "λ", "mu": "μ", "pi": "π", "sigma": "σ", "omega": "ω", "Delta": "Δ",
    "Omega": "Ω", "Gamma": "Γ", "Sigma": "Σ", "times": "×", "pm": "±", "circ": "°",
    "degree": "°", "rightarrow": "→", "to": "→", "approx": "≈", "sim": "∼", "cdot": "·",
    "ldots": "…", "dots": "…", "LaTeX": "LaTeX", "TeX": "TeX",
}
IGNORE_WITH_ARG = {"vspace", "hspace", "setlength", "label", "cite", "ref", "footnote",
                   "section", "subsection", "newpage", "pagestyle", "thispagestyle",
                   "hypersetup", "usepackage", "documentclass", "bibliographystyle", "bibliography"}
PLAIN_ARG = {"text", "textrm", "textsf", "texttt", "textsc", "mathrm", "mathbf", "mbox", "hbox", "mathsf"}
EMPH_ARG = {"textit", "emph", "textsl", "mathit"}
BOLD_ARG = {"textbf"}
UNDERLINE_ARG = {"underline", "uline", "ul"}


def read_group(s, i):
    """s[i] == '{'. Return (content, index after the matching '}')."""
    depth = 0
    j = i
    while j < len(s):
        c = s[j]
        if c == "\\":
            j += 2
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return s[i + 1:j], j + 1
        j += 1
    return s[i + 1:], len(s)


def take_arg(s, i):
    while i < len(s) and s[i] in " \t\n":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] == "{":
        return read_group(s, i)
    if s[i] == "\\":
        m = re.match(r"\\[A-Za-z]+", s[i:])
        if m:
            return m.group(0), i + len(m.group(0))
        return s[i:i + 2], i + 2
    return s[i], i + 1


def accent(comb, arg):
    arg = arg.strip()
    if arg in ("\\i", "\\j"):
        arg = arg[1]
    arg = re.sub(r"[{}]", "", arg)
    if not arg:
        return ""
    return unicodedata.normalize("NFC", arg[0] + comb) + arg[1:]


def unescape_url(u):
    return re.sub(r"\\([%&#_$])", r"\1", u).strip()


def render(s):
    out = []
    i, n = 0, len(s)
    math = False
    while i < n:
        c = s[i]
        if c == "\\":
            if i + 1 >= n:
                break
            nxt = s[i + 1]
            if nxt.isalpha():
                name = re.match(r"[A-Za-z]+", s[i + 1:]).group(0)
                i += 1 + len(name)
                if name in UNDERLINE_ARG:
                    arg, i = take_arg(s, i)
                    out.append('<span class="me">' + render(arg) + "</span>")
                elif name in BOLD_ARG:
                    arg, i = take_arg(s, i)
                    out.append("<strong>" + render(arg) + "</strong>")
                elif name in EMPH_ARG:
                    arg, i = take_arg(s, i)
                    out.append("<em>" + render(arg) + "</em>")
                elif name in PLAIN_ARG:
                    arg, i = take_arg(s, i)
                    out.append(render(arg))
                elif name == "href":
                    url, i = take_arg(s, i)
                    text, i = take_arg(s, i)
                    out.append('<a href="%s">%s</a>' % (html.escape(unescape_url(url), quote=True), render(text)))
                elif name == "url":
                    url, i = take_arg(s, i)
                    u = unescape_url(url)
                    out.append('<a href="%s">%s</a>' % (html.escape(u, quote=True), html.escape(u)))
                elif name == "doi":
                    d, i = take_arg(s, i)
                    d = unescape_url(d)
                    out.append('<a href="https://doi.org/%s">doi:%s</a>' % (html.escape(d, quote=True), html.escape(d)))
                elif name in ACCENTS and len(name) == 1:
                    arg, i = take_arg(s, i)
                    out.append(html.escape(accent(ACCENTS[name], arg)))
                elif name in LETTER_SPECIALS:
                    out.append(LETTER_SPECIALS[name])
                    if i < n and s[i] == " ":
                        i += 1
                elif name in IGNORE_WITH_ARG:
                    while i < n and s[i] in " \t":
                        i += 1
                    if i < n and s[i] == "[":
                        j = s.find("]", i)
                        i = j + 1 if j != -1 else n
                    if i < n and s[i] == "{":
                        _, i = read_group(s, i)
                else:
                    # unknown command: drop the name, keep going (its argument, if any, still renders)
                    if i < n and s[i] == " ":
                        i += 1
                continue
            # non-letter control sequences
            if nxt in "&%$#_{}":
                out.append(html.escape(nxt))
                i += 2
            elif nxt in ACCENTS:
                arg, i2 = take_arg(s, i + 2)
                out.append(html.escape(accent(ACCENTS[nxt], arg)))
                i = i2
            elif nxt == "\\":
                out.append(" ")
                i += 2
            elif nxt in ",;:! ":
                out.append("\u2009" if nxt in ",;:" else "" if nxt == "!" else " ")
                i += 2
            else:
                i += 2
            continue
        if c == "{":
            g, i = read_group(s, i)
            m = re.match(r"\s*\\(bf|bfseries|it|itshape|em|sl|sc|rm|ul)\b\s?", g)
            if m:
                inner = render(g[m.end():])
                tag = {"bf": "strong", "bfseries": "strong", "it": "em", "itshape": "em",
                       "em": "em", "sl": "em", "ul": None, "sc": None, "rm": None}[m.group(1)]
                out.append("<%s>%s</%s>" % (tag, inner, tag) if tag else inner)
            else:
                out.append(render(g))
            continue
        if c == "}":
            i += 1
            continue
        if c == "$":
            math = not math
            i += 1
            continue
        if c in "_^" and math:
            arg, i = take_arg(s, i + 1)
            tag = "sub" if c == "_" else "sup"
            out.append("<%s>%s</%s>" % (tag, render(arg), tag))
            continue
        if c == "~":
            out.append("\u00a0")
            i += 1
            continue
        if s.startswith("---", i):
            out.append("—")
            i += 3
            continue
        if s.startswith("--", i):
            out.append("–")
            i += 2
            continue
        if s.startswith("``", i):
            out.append("“")
            i += 2
            continue
        if s.startswith("''", i):
            out.append("”")
            i += 2
            continue
        if c == "`":
            out.append("‘")
            i += 1
            continue
        out.append(html.escape(c))
        i += 1
    return "".join(out)


def strip_comments(tex):
    return re.sub(r"(?<!\\)%.*", "", tex)


def split_entries(tex):
    tex = strip_comments(tex)
    m = re.search(r"\\begin\{document\}(.*)\\end\{document\}", tex, re.S)
    if m:
        tex = m.group(1)
    tex = re.sub(r"\\(begin|end)\{(thebibliography|enumerate|itemize|description)\}(\{[^}]*\})?", "", tex)
    splitter = re.compile(r"\\item\b(\s*\[[^\]]*\])?|\\bibitem(\s*\[[^\]]*\])?\s*\{[^}]*\}")
    if splitter.search(tex):
        chunks = splitter.split(tex)
        chunks = [c for c in chunks if c is not None and not re.fullmatch(r"\s*\[[^\]]*\]\s*", c or "")]
    else:
        chunks = re.split(r"\n\s*\n", tex)
    entries = []
    for ch in chunks:
        ch = re.sub(r"\s+", " ", ch).strip()
        if ch:
            entries.append(ch)
    return entries


def guess_year(rendered_html):
    plain = re.sub(r"<[^>]+>", " ", rendered_html)
    plain = re.sub(r"https?://\S+|\S*/\S*", " ", plain)
    years = re.findall(r"(?<!\d)(19[89]\d|20[0-3]\d)(?!\d)", plain)
    return years[-1] if years else None


def build(entries):
    items = []
    for e in entries:
        h = render(e).strip()
        h = re.sub(r"\s+", " ", h)
        if h and not h.endswith((".", "</a>")):
            h = re.sub(r"[\s,;]+$", "", h) + "."
        items.append((h, guess_year(h)))
    if not items:
        return '<p class="placeholder">Publication list coming soon.</p>'

    total = len(items)
    any_year = any(y for _, y in items)
    blocks = []
    current_year, current = None, []

    def flush():
        if current:
            head = "<h3>%s</h3>\n    " % current_year if current_year else ""
            blocks.append('<div class="pub-year">\n    %s<ol class="pubs">\n%s\n    </ol>\n</div>'
                          % (head, "\n".join(current)))

    number = total
    for h, y in items:
        if any_year:
            y = y or current_year
            if y != current_year:
                flush()
                current_year, current = y, []
        current.append('        <li value="%d">%s</li>' % (number, h))
        number -= 1
    flush()
    return "\n".join(blocks)


def main():
    ap = argparse.ArgumentParser(description="Insert a LaTeX publication list into publications.html")
    ap.add_argument("tex", help="LaTeX file with the publication list")
    ap.add_argument("--html", help="target HTML file (default: ../publications.html next to this script)")
    args = ap.parse_args()

    target = Path(args.html) if args.html else Path(__file__).resolve().parent.parent / "publications.html"
    tex = Path(args.tex).read_text(encoding="utf-8")
    entries = split_entries(tex)
    body = build(entries)

    page = target.read_text(encoding="utf-8")
    pattern = re.compile(r"(<!-- PUBS:START -->)(.*?)(<!-- PUBS:END -->)", re.S)
    if not pattern.search(page):
        sys.exit("Markers <!-- PUBS:START --> / <!-- PUBS:END --> not found in %s" % target)
    page = pattern.sub(lambda m: "%s\n%s\n        %s" % (m.group(1), body, m.group(3)), page, count=1)
    target.write_text(page, encoding="utf-8")
    print("Wrote %d publications to %s" % (len(entries), target))


if __name__ == "__main__":
    main()
