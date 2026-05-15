from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUIDE_DIR = ROOT / "learning_guides"
TEX_DIR = GUIDE_DIR / "tex"
PDF_DIR = GUIDE_DIR / "pdf"
HTML_DIR = GUIDE_DIR / "html"
BUILD_DIR = GUIDE_DIR / "_latex_build"


LATEX_PREAMBLE = r"""
\documentclass[UTF8,12pt,a4paper]{ctexart}
\usepackage[margin=2.2cm]{geometry}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{fontspec}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyvrb}
\usepackage{fvextra}
\usepackage{microtype}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{setspace}

\hypersetup{
  colorlinks=true,
  linkcolor=blue!55!black,
  urlcolor=blue!55!black
}

\setstretch{1.18}
\setlist[itemize]{leftmargin=1.8em,itemsep=0.25em,topsep=0.3em}
\setlist[enumerate]{leftmargin=2.1em,itemsep=0.25em,topsep=0.3em}
\titleformat{\section}{\Large\bfseries}{\thesection}{0.8em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{0.8em}{}
\titleformat{\subsubsection}{\normalsize\bfseries}{\thesubsubsection}{0.8em}{}
\pagestyle{fancy}
\fancyhf{}
\fancyfoot[C]{\thepage}
\renewcommand{\headrulewidth}{0pt}

\DefineVerbatimEnvironment{GuideVerbatim}{Verbatim}{
  breaklines=true,
  breakanywhere=true,
  fontsize=\small,
  frame=single,
  framesep=3mm,
  rulecolor=\color{gray!35},
  bgcolor=gray!7
}

\newcommand{\GuideInlineCode}[1]{\texttt{\detokenize{#1}}}

\begin{document}
"""


LATEX_END = r"\end{document}" + "\n"


SPECIAL_CHARS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}


def latex_escape(text: str) -> str:
    return "".join(SPECIAL_CHARS.get(char, char) for char in text)


def latex_inline(text: str) -> str:
    """Convert a small Markdown inline subset to LaTeX."""
    pieces: list[str] = []
    pos = 0
    pattern = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))")
    for match in pattern.finditer(text):
        pieces.append(latex_escape(text[pos : match.start()]))
        token = match.group(0)
        if token.startswith("`"):
            pieces.append(r"\texttt{" + latex_escape(token[1:-1]) + "}")
        elif token.startswith("**"):
            pieces.append(r"\textbf{" + latex_inline(token[2:-2]) + "}")
        else:
            link = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            if link:
                label = latex_escape(link.group(1))
                url = latex_escape(link.group(2))
                pieces.append(r"\href{" + url + "}{" + label + "}")
        pos = match.end()
    pieces.append(latex_escape(text[pos:]))
    return "".join(pieces)


def latex_math_identifier(token: str) -> str:
    if "_" not in token:
        return token
    head, tail = token.split("_", 1)
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", head) and re.fullmatch(r"[A-Za-z0-9]+", tail):
        return f"{head}_{{{tail}}}"
    return token


def latex_math_line(line: str) -> str:
    stripped = line.strip()
    stripped = stripped.replace("<=", r"\le")
    stripped = stripped.replace(">=", r"\ge")
    stripped = stripped.replace("!=", r"\ne")
    stripped = stripped.replace("<->", r"\leftrightarrow")
    stripped = stripped.replace("->", r"\to")
    stripped = stripped.replace("*", r"\cdot ")
    stripped = re.sub(r"\bin\b", r"\\in", stripped)
    stripped = re.sub(r"\bsum_\{([^}]+)\}", r"\\sum_{\1}", stripped)
    stripped = re.sub(r"\bsum_([A-Za-z0-9]+)", r"\\sum_{\1}", stripped)
    stripped = re.sub(r"\bproduct_([A-Za-z0-9]+)", r"\\prod_{\1}", stripped)
    stripped = re.sub(r"\bexp\(", r"\\exp(", stripped)
    stripped = re.sub(r"\|psi\(([^)]+)\)>", r"|\\psi(\1)\\rangle", stripped)
    stripped = re.sub(r"\|\+\>\^n", r"|+\\rangle^{\\otimes n}", stripped)
    stripped = re.sub(r"(\\in\s*)\{([^{}]*)\}", lambda m: m.group(1) + r"\{" + m.group(2) + r"\}", stripped)
    stripped = re.sub(
        r"\b[A-Za-z]+_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)?\b",
        lambda m: latex_math_identifier(m.group(0)),
        stripped,
    )
    stripped = re.sub(r"\b([A-Za-z])([0-9]+)\b", r"\1_{\2}", stripped)
    stripped = stripped.replace("minimize", r"\operatorname*{minimize}")
    stripped = stripped.replace("maximize", r"\operatorname*{maximize}")
    stripped = stripped.replace("subject to", r"\operatorname*{subject\ to}")
    stripped = stripped.replace("binary variables:", r"\text{binary variables:}")
    stripped = stripped.replace("spin variables:", r"\text{spin variables:}")
    stripped = stripped.replace("linear bias:", r"\text{linear bias:}")
    stripped = stripped.replace("quadratic bias:", r"\text{quadratic bias:}")
    stripped = stripped.replace("offset:", r"\text{offset:}")
    return stripped


def looks_like_math_block(lines: list[str]) -> bool:
    if not lines:
        return False
    joined = "\n".join(line.strip() for line in lines if line.strip())
    if not joined:
        return False
    if re.search(r"[\u4e00-\u9fff]", joined):
        return False
    if "->" in joined and not re.search(r"[=+\-*/^_{}]", joined):
        return False
    math_tokens = [
        "minimize",
        "maximize",
        "subject to",
        "sum_",
        "product_",
        " in ",
        "<=",
        ">=",
        "=",
        "H(",
        "E(",
        "|psi",
        "x_",
        "s_",
        "q_",
        "J_",
        "H_",
    ]
    return any(token in joined for token in math_tokens)


def render_math_block(lines: list[str]) -> list[str]:
    rendered = [latex_math_line(line) for line in lines if line.strip()]
    if len(rendered) == 1:
        return [r"\[", rendered[0], r"\]"]
    return [r"\[", r"\begin{aligned}", *[line + r"\\" for line in rendered[:-1]], rendered[-1], r"\end{aligned}", r"\]"]


def flush_paragraph(paragraph: list[str], output: list[str]) -> None:
    if paragraph:
        output.append(latex_inline(" ".join(part.strip() for part in paragraph if part.strip())))
        output.append("")
        paragraph.clear()


def flush_list(items: list[str], output: list[str], ordered: bool) -> None:
    if not items:
        return
    env = "enumerate" if ordered else "itemize"
    output.append(r"\begin{" + env + "}")
    for item in items:
        output.append(r"\item " + latex_inline(item))
    output.append(r"\end{" + env + "}")
    output.append("")
    items.clear()


def markdown_to_latex(markdown_text: str) -> str:
    output: list[str] = [LATEX_PREAMBLE]
    paragraph: list[str] = []
    list_items: list[str] = []
    list_ordered = False
    code_lines: list[str] = []
    in_code = False

    def close_text_blocks() -> None:
        flush_paragraph(paragraph, output)
        flush_list(list_items, output, list_ordered)

    for raw_line in markdown_text.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            if in_code:
                if looks_like_math_block(code_lines):
                    output.extend(render_math_block(code_lines))
                    output.append("")
                else:
                    output.append(r"\begin{GuideVerbatim}")
                    output.extend(code_lines)
                    output.append(r"\end{GuideVerbatim}")
                    output.append("")
                code_lines.clear()
                in_code = False
            else:
                close_text_blocks()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            close_text_blocks()
            continue

        heading = re.match(r"^(#{1,3})\s+(.*)$", line)
        if heading:
            close_text_blocks()
            level = len(heading.group(1))
            command = {1: "section*", 2: "subsection*", 3: "subsubsection*"}[level]
            output.append(r"\%s{%s}" % (command, latex_inline(heading.group(2))))
            output.append("")
            continue

        unordered = re.match(r"^-\s+(.*)$", line)
        ordered = re.match(r"^\d+\.\s+(.*)$", line)
        if unordered or ordered:
            flush_paragraph(paragraph, output)
            current_ordered = bool(ordered)
            if list_items and current_ordered != list_ordered:
                flush_list(list_items, output, list_ordered)
            list_ordered = current_ordered
            list_items.append((ordered or unordered).group(1))
            continue

        if line.startswith("> "):
            close_text_blocks()
            output.append(r"\begin{quote}")
            output.append(latex_inline(line[2:]))
            output.append(r"\end{quote}")
            output.append("")
            continue

        paragraph.append(line)

    close_text_blocks()
    output.append(LATEX_END)
    return "\n".join(output)


def find_xelatex() -> Path:
    known_paths = [
        Path.home() / "AppData" / "Local" / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64" / "xelatex.exe",
        Path(r"C:\Program Files\MiKTeX\miktex\bin\x64\xelatex.exe"),
        Path(r"C:\Program Files (x86)\MiKTeX\miktex\bin\x64\xelatex.exe"),
    ]
    for known_path in known_paths:
        if known_path.exists():
            return known_path
    found = shutil.which("xelatex")
    if found:
        return Path(found)
    raise FileNotFoundError("xelatex was not found. Install MiKTeX or TeX Live first.")


def clean_legacy_outputs() -> None:
    if HTML_DIR.exists():
        shutil.rmtree(HTML_DIR)


def build_tex_files(markdown_files: list[Path]) -> list[Path]:
    TEX_DIR.mkdir(parents=True, exist_ok=True)
    tex_files: list[Path] = []
    for stale in TEX_DIR.glob("*.tex"):
        stale.unlink()
    for md_file in markdown_files:
        tex_text = markdown_to_latex(md_file.read_text(encoding="utf-8"))
        tex_file = TEX_DIR / f"{md_file.stem}.tex"
        tex_file.write_text(tex_text, encoding="utf-8")
        tex_files.append(tex_file)
    return tex_files


def run_xelatex(tex_file: Path, xelatex: Path) -> None:
    job_build_dir = BUILD_DIR / tex_file.stem
    job_build_dir.mkdir(parents=True, exist_ok=True)
    command = [
        str(xelatex),
        "--miktex-enable-installer",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-output-directory={job_build_dir}",
        str(tex_file.resolve()),
    ]
    for _ in range(2):
        subprocess.run(command, check=True, cwd=ROOT)
    produced_pdf = job_build_dir / f"{tex_file.stem}.pdf"
    target_pdf = PDF_DIR / produced_pdf.name
    if not produced_pdf.exists():
        raise RuntimeError(f"XeLaTeX did not produce {produced_pdf}")
    shutil.copy2(produced_pdf, target_pdf)
    if target_pdf.stat().st_size < 10_000:
        raise RuntimeError(f"Generated PDF is unexpectedly small: {target_pdf}")


def build_pdfs(tex_files: list[Path]) -> None:
    xelatex = find_xelatex()
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    for stale in PDF_DIR.glob("*.pdf"):
        stale.unlink()
    for tex_file in tex_files:
        run_xelatex(tex_file, xelatex)


def main() -> int:
    markdown_files = sorted(GUIDE_DIR.glob("[0-9][0-9]_*.md"))
    if not markdown_files:
        print("No learning guide Markdown files found.", file=sys.stderr)
        return 1
    clean_legacy_outputs()
    tex_files = build_tex_files(markdown_files)
    build_pdfs(tex_files)
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    print(f"Built {len(tex_files)} TeX files in {TEX_DIR}")
    print(f"Built {len(tex_files)} PDF files in {PDF_DIR}")
    print(f"Legacy HTML directory removed: {not HTML_DIR.exists()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
