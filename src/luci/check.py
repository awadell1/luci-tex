import re
import typer
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable, Sequence, Optional


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Location:
    file: Path | None = None
    line: int | None = None
    page: str | None = None


@dataclass(frozen=True)
class Issue:
    kind: str
    message: str
    severity: Severity
    source: Path | None = None
    locations: tuple[Location, ...] = field(default_factory=tuple)


# Note: detectors are implemented as functions below for clarity and testability.


_OVERFULL_RE = re.compile(
    r"Overfull \\([hv])box \(([-\d.]+)pt too (?:wide|high)\)(?:.*? at lines? (\d+)(?:--(\d+))?)?",
)

# Context helpers
# Match file opens that look like source files with a directory component,
# e.g. (./main.tex, (chapters/intro.tex, or (vendor/mist/sections/scaling
_PAREN_FILE_RE = re.compile(r"\(((?:\.{0,2}/)?[^()\s]*/[^()\s]*)")
_INPUT_LINE_RE = re.compile(r"on input line\s+(\d+)")
_ON_PAGE_RE = re.compile(r"on page\s+([ivxlcdmIVXLCDM\d]+)")
# Page shipout markers like [12] or [xi]
_PAGE_MARK_RE = re.compile(r"\[\s*([ivxlcdmIVXLCDM\d]+)\s*\]")
_PAGE_START_RE = re.compile(r"^\s*\[\s*([ivxlcdmIVXLCDM\d]+)\s*$")
_PAGE_END_RE = re.compile(r"^\s*\]\s*$")


# Helpers: context and page inference
def _iter_file_context(lines: list[str]) -> list[Path | None]:
    context: list[Path | None] = [None] * len(lines)
    stack: list[Path | None] = []
    for idx, line in enumerate(lines):
        j = 0
        L = len(line)
        while j < L:
            ch = line[j]
            if ch == "(":
                m = _PAREN_FILE_RE.match(line, j)
                if m:
                    raw = m.group(1)
                    p = Path(raw)
                    if p.suffix not in {".tex", ".ltx"}:
                        p = p.with_suffix(".tex")
                    stack.append(p)
                    j = m.end()
                    continue
                else:
                    stack.append(None)
            elif ch == ")":
                if stack:
                    stack.pop()
            j += 1
        current = next((p for p in reversed(stack) if isinstance(p, Path)), None)
        context[idx] = current
    return context


def _next_page_label(lines: list[str], start: int) -> str | None:
    end = min(len(lines), start + 10)
    for j in range(start, end):
        ln = lines[j]
        for m in _PAGE_MARK_RE.finditer(ln):
            return m.group(1)
        m2 = _PAGE_START_RE.match(ln)
        if m2:
            return m2.group(1)
    return None


def _merge_issue(existing: Issue | None, inc: Issue) -> Issue:
    if existing is None:
        return inc
    order = [Severity.INFO, Severity.WARNING, Severity.ERROR]
    sev = existing.severity
    if order.index(inc.severity) > order.index(sev):
        sev = inc.severity
    merged = list(existing.locations)
    for loc in inc.locations:
        for idx, el in enumerate(merged):
            if el.file == loc.file and el.line == loc.line:
                if el.page is None and loc.page is not None:
                    merged[idx] = Location(file=el.file, line=el.line, page=loc.page)
                break
        else:
            if loc not in merged:
                merged.append(loc)
    return Issue(
        kind=existing.kind,
        message=existing.message,
        severity=sev,
        source=existing.source,
        locations=tuple(merged),
    )


# Detectors
def _detect_citation(lines: list[str], i: int, line: str, current_file: Path | None) -> Issue | None:
    if "Warning: Citation" not in line or "undefined" not in line:
        return None
    m_key = re.search(r"[`'](.+?)['`]", line)
    if not m_key:
        return None
    key = m_key.group(1)
    lookahead = line + (lines[i + 1] if i + 1 < len(lines) else "")
    m_line = _INPUT_LINE_RE.search(lookahead)
    page_label = _next_page_label(lines, i)
    loc = Location(
        file=current_file if (m_line is not None) else None,
        line=int(m_line.group(1)) if m_line else None,
        page=page_label,
    )
    return Issue("Undefined citation", key, Severity.WARNING, None, (loc,))


def _detect_reference(lines: list[str], i: int, line: str, current_file: Path | None) -> Issue | None:
    if "LaTeX Warning:" not in line or "undefined" not in line:
        return None
    if " Reference " not in line and " Hyper reference " not in line:
        return None
    lookahead = line + (lines[i + 1] if i + 1 < len(lines) else "")
    m_key = re.search(r"(?:Hyper )?Reference [`']([^`']+)[`']", lookahead)
    if not m_key:
        return None
    key = m_key.group(1)
    m_line = _INPUT_LINE_RE.search(lookahead)
    page_label = _next_page_label(lines, i)
    loc = Location(
        file=current_file if (m_line is not None) else None,
        line=int(m_line.group(1)) if m_line else None,
        page=page_label,
    )
    return Issue("Undefined reference", key, Severity.WARNING, None, (loc,))


def _detect_missing_file(lines: list[str], i: int, line: str, current_file: Path | None) -> Issue | None:
    if "! LaTeX Error: File" not in line or "not found" not in line:
        return None
    m_key = re.search(r"File [`'](.+?)['`] not found", line)
    filename = m_key.group(1) if m_key else "unknown"
    m_lnum = re.search(r"^l\.(\d+)", lines[i + 1]) if (i + 1) < len(lines) else None
    loc = Location(
        file=current_file if (m_lnum is not None) else None,
        line=int(m_lnum.group(1)) if m_lnum else None,
        page=None,
    )
    return Issue("Missing file", filename, Severity.ERROR, None, (loc,))


def _detect_overfull(line: str, current_file: Path | None, *, threshold_pt: float) -> Issue | None:
    m_over = _OVERFULL_RE.search(line)
    if not m_over:
        return None
    axis, pts, lstart, _ = m_over.groups()
    try:
        mag = float(pts)
    except ValueError:
        return None
    if mag < threshold_pt:
        return None
    kind = "Overfull hbox" if axis == "h" else "Overfull vbox"
    line_num = int(lstart) if lstart else None
    loc = Location(file=current_file if line_num else None, line=line_num, page=None)
    return Issue(kind, f"{mag:.1f}pt", Severity.WARNING, None, (loc,))


def _scan_single_log(log_path: Path, *, overflow_threshold_pt: float) -> list[Issue]:
    text = log_path.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()
    context = _iter_file_context(lines)

    collected: dict[tuple[str, str], Issue] = {}
    for i, line in enumerate(lines):
        current = context[i]

        for det in (_detect_citation, _detect_reference, _detect_missing_file):
            iss = det(lines, i, line, current)
            if iss is None:
                continue
            # ensure source is the log file
            iss = Issue(iss.kind, iss.message, iss.severity, log_path, iss.locations)
            key = (iss.kind, iss.message)
            collected[key] = _merge_issue(collected.get(key), iss)

        over = _detect_overfull(line, current, threshold_pt=overflow_threshold_pt)
        if over is not None:
            over = Issue(over.kind, over.message, over.severity, log_path, over.locations)
            key = (over.kind, over.message)
            collected[key] = _merge_issue(collected.get(key), over)

    return list(collected.values())


def find_logs(paths: Sequence[Path] | None, base_dir: Path | None) -> list[Path]:
    # Prefer explicit list
    if paths:
        return [p for p in paths if p.suffix == ".log" and p.exists()]
    # Otherwise search base_dir (or cwd)
    root = base_dir or Path.cwd()
    return sorted(root.rglob("*.log"))


def scan_logs(logs: Iterable[Path], *, overflow_threshold_pt: float) -> list[Issue]:
    collected: dict[tuple[str, str], Issue] = {}
    for log in logs:
        try:
            found = _scan_single_log(log, overflow_threshold_pt=overflow_threshold_pt)
        except FileNotFoundError:
            continue
        for iss in found:
            key = (iss.kind, iss.message)
            collected[key] = _merge_issue(collected.get(key), iss)
    return list(collected.values())


def check(
    logs: Optional[list[Path]] = typer.Argument(
        None,
        help="One or more .log files to scan (shell globs supported). If omitted, searches ./build or CWD.",
    ),
    build_dir: Optional[Path] = typer.Option(
        None,
        help="Directory to search for LaTeX .log files when no files are provided. Defaults to ./build if present, else CWD.",
    ),
    overflow_threshold_pt: float = typer.Option(
        10.0, help="Only flag overfull boxes >= this many points."
    ),
    strict: bool = typer.Option(
        False, help="Treat warnings as errors for exit status."
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output issues as JSON for tooling/CI (suppresses human output).",
    ),
):
    """
    Check build artifacts for common LaTeX problems with low false positives.

    - Scans .log files for undefined citations, references, and missing files.
    - Flags overfull h/v boxes above a configurable threshold (in points).

    Exit status is non-zero if any errors are found (or warnings when --strict).
    """
    # Default base: prefer ./build if it exists
    if build_dir is None:
        candidate = Path("build")
        build_dir = candidate if candidate.exists() else Path.cwd()

    found_logs = find_logs(logs, build_dir)
    if not found_logs:
        if json_output:
            typer.echo(json.dumps({"issues": []}, indent=2))
        else:
            typer.echo("No .log files found to scan.")
        raise typer.Exit(code=0)

    issues = scan_logs(found_logs, overflow_threshold_pt=overflow_threshold_pt)

    def _display_path(p: Path) -> str:
        s = str(p)
        if p.is_absolute():
            try:
                s = str(p.relative_to(Path.cwd()))
            except ValueError:
                s = str(p)
        if s.startswith("./"):
            s = s[2:]
        return s

    def _format_loc_line(loc: Location) -> str | None:
        parts: list[str] = []
        if loc.file and loc.line:
            parts.append(f"{_display_path(loc.file)}:{loc.line}")
        elif loc.file:
            parts.append(_display_path(loc.file))
        elif loc.line:
            parts.append(f"line {loc.line}")
        if loc.page:
            parts.append(f"p.{loc.page}")
        return " ".join(parts) if parts else None

    if json_output:
        def _loc_to_obj(loc: Location) -> dict:
            obj: dict = {}
            if loc.file is not None:
                obj["file"] = _display_path(loc.file)
            if loc.line is not None:
                obj["line"] = loc.line
            if loc.page is not None:
                obj["page"] = loc.page
            return obj

        payload = {
            "issues": [
                {
                    "kind": issue.kind,
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "locations": [_loc_to_obj(loc) for loc in issue.locations],
                }
                for issue in issues
            ]
        }
        typer.echo(json.dumps(payload, indent=2))
    elif issues:
        for issue in issues:
            prefix = (
                "ERROR" if issue.severity == Severity.ERROR else "WARN"
                if issue.severity == Severity.WARNING
                else "INFO"
            )
            typer.echo(f"{prefix}: {issue.kind}: {issue.message}")
            if issue.locations:
                for loc in issue.locations:
                    line = _format_loc_line(loc)
                    if line:
                        typer.echo(f"  - {line}")

    # Exit code semantics
    has_error = any(i.severity == Severity.ERROR for i in issues)
    has_warning = any(i.severity == Severity.WARNING for i in issues)

    if has_error or (strict and has_warning):
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)
