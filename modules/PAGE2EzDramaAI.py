import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Callable

try:
    from modules.config import PAGE_XML_NS as ns, REGION_TYPE_PREFIX as type_prefix
    from modules.drama_context import DramaContext
    from modules.llm import cached_call
except ImportError:
    from config import PAGE_XML_NS as ns, REGION_TYPE_PREFIX as type_prefix
    from drama_context import DramaContext
    from llm import cached_call


def _extract_raw_lines(filepath: str) -> list[tuple[float, int, str]]:
    """Liest alle TextLines eines PAGE-XML in Lesereihenfolge, ohne Typ-/Präfixlogik
    (Regionen sind im KI-Modus untypisiert). Rückgabeform identisch zu
    `PAGE2EzDrama.extract_lines()`, damit dieselbe Zeilengruppierung weiterverwendet
    werden kann."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    lines_data: list[tuple[float, int, str]] = []

    for region in root.findall(".//pc:TextRegion", ns):
        for line in region.findall("pc:TextLine", ns):
            coords_el = line.find("pc:Coords", ns)
            if coords_el is None:
                continue
            points_str = coords_el.attrib.get("points", "")
            if not points_str.strip():
                continue
            try:
                coords = [tuple(map(int, pt.split(","))) for pt in points_str.strip().split()]
            except ValueError:
                continue
            xs = [x for x, y in coords]
            ys = [y for x, y in coords]
            x_min = min(xs)
            y_center = sum(ys) / len(ys)

            text_equivs = line.findall("pc:TextEquiv", ns)
            text_equiv = None
            for te in text_equivs:
                if te.attrib.get("index") == "0":
                    text_equiv = te
                    break
            if text_equiv is None and text_equivs:
                text_equiv = text_equivs[-1]

            if text_equiv is None:
                continue
            uni = text_equiv.find("pc:Unicode", ns)
            if uni is None or not (uni.text and uni.text.strip()):
                continue

            lines_data.append((y_center, x_min, uni.text))

    return lines_data


def _build_prompt(raw_lines: list[tuple[float, int, str]], context: DramaContext) -> str:
    numbered = "\n".join(f'{i}: "{text}"' for i, (_, _, text) in enumerate(raw_lines))
    known = ", ".join(context.known_speakers) if context.known_speakers else "(noch keine)"

    return f"""Du analysierst automatisch erstelltes OCR von historischen Dramentexten (ca. 1650–1850)
ohne manuelle Segmentierungs-Codierung. Jede Zeile muss klassifiziert werden.

Kategorien:
- "noise"           Unlesbares OCR-Artefakt / Verzierung — wird verworfen
- "page_number"     Reine Seitenzahl / Kolumnentitel — wird verworfen
- "heading"         Akt-/Szenenüberschrift (z.B. "Erster Aufzug", "Vierter Auftritt")
- "speaker_list"    Aufzählung auftretender Figuren, keine Dialogzeile (z.B. "Simplex. Candidus. Fideliis.")
                    → gib die einzelnen Namen zusätzlich als Liste "names" zurück
- "stage_direction" Regieanweisung, eigenständig oder Teil einer mehrzeiligen Klammer
- "dialogue"        Gesprochener Text; falls die Zeile mit einem Sprecherkürzel beginnt,
                    dieses Kürzel separat als "speaker" angeben

Bekannter Kontext: aktueller Sprecher = {context.current_speaker!r}, offene Klammer = {context.open_stage_direction}
Bereits bekannte Sprecherkandidaten: {known}

Antworte NUR mit JSON in genau dieser Form:
{{
  "lines": [{{"i": 0, "label": "...", "speaker": "..." oder null, "names": ["..."] oder null}}],
  "context_out": {{"current_speaker": "..." oder null, "open_stage_direction": true oder false}}
}}

Zeilen:
{numbered}
"""


@dataclass
class AIPageResult:
    lines_data: list[tuple[float, int, str]]
    speaker_list_raw: set[str]
    speaker_examples: dict[str, str]
    figure_names: set[str]
    context: DramaContext
    error: str | None = None


def classify_page_ai(filepath: str, context: DramaContext, model: str) -> AIPageResult:
    """Klassifiziert alle Zeilen einer PAGE-XML-Datei per LLM in einem einzigen Aufruf
    und leitet daraus sowohl die EzDrama-kompatible Zeilenliste als auch die
    Sprecherkandidaten/Figurennamen für die Interaktive Validierung ab."""
    raw_lines = _extract_raw_lines(filepath)
    if not raw_lines:
        return AIPageResult([], set(), {}, set(), context)

    prompt = _build_prompt(raw_lines, context)
    cache_key = f"{filepath}::{model}::{prompt}"
    error_out: dict = {}
    result = cached_call(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        cache_key=cache_key,
        json_mode=True,
        error_out=error_out,
    )

    if result is None:
        # Fallback: Seite komplett als unpräfigierten Fließtext übernehmen,
        # nichts geht verloren — Korrektur erfolgt manuell im Text-Editor.
        return AIPageResult(
            list(raw_lines), set(), {}, set(), context,
            error=error_out.get("error", "Unbekannter Fehler bei der KI-Klassifikation."),
        )

    labels_by_index = {item.get("i"): item for item in result.get("lines", [])}

    lines_data: list[tuple[float, int, str]] = []
    speaker_list_raw: set[str] = set()
    speaker_examples: dict[str, str] = {}
    figure_names: set[str] = set()

    for idx, (y, x, text) in enumerate(raw_lines):
        item = labels_by_index.get(idx) or {"label": "dialogue"}
        label = item.get("label", "dialogue")

        if label in ("noise", "page_number"):
            continue
        elif label == "heading":
            lines_data.append((y, x, f"{type_prefix['header']}{text}"))
        elif label == "speaker_list":
            lines_data.append((y, x, f"{type_prefix['catch-word']}{text}"))
            for name in item.get("names") or []:
                cleaned = re.sub(r"[^\w\s]", "", name).replace("ſ", "s").strip().lower()
                if cleaned:
                    figure_names.add(cleaned)
        elif label == "stage_direction":
            lines_data.append((y, x, f"{type_prefix['signature-mark']}{text}"))
        else:  # dialogue
            lines_data.append((y, x, text))
            speaker = item.get("speaker")
            if speaker:
                speaker_list_raw.add(speaker)
                cleaned = re.sub(r"[^\w\s]", "", speaker).strip().lower()
                if cleaned and cleaned not in speaker_examples:
                    speaker_examples[cleaned] = text

    context_out = result.get("context_out") or {}
    known = sorted(set(context.known_speakers) | speaker_list_raw)
    new_context = DramaContext(
        current_speaker=context_out.get("current_speaker"),
        open_stage_direction=bool(context_out.get("open_stage_direction", False)),
        known_speakers=known,
    )

    return AIPageResult(lines_data, speaker_list_raw, speaker_examples, figure_names, new_context)


def extract_lines_ai(
    filepath: str, context: DramaContext, model: str
) -> tuple[list[tuple[float, int, str]], DramaContext]:
    """Dünner Wrapper um `classify_page_ai()` mit derselben Rückgabeform wie
    `PAGE2EzDrama.extract_lines()` (plus fortgeschriebenem Kontext) — Andockpunkt
    für `line_extractor` in `process_file()`/`page2ezdrama()`."""
    result = classify_page_ai(filepath, context, model)
    return result.lines_data, result.context


def make_ai_line_extractor(
    model: str, initial_context: DramaContext | None = None
) -> Callable[[str], list[tuple[float, int, str]]]:
    """Baut einen `line_extractor` für `page2ezdrama(line_extractor=...)`, der den
    DramaContext seitenübergreifend (in Aufrufreihenfolge) mitführt."""
    state = {"context": initial_context or DramaContext()}

    def _extractor(filepath: str) -> list[tuple[float, int, str]]:
        lines_data, state["context"] = extract_lines_ai(filepath, state["context"], model)
        return lines_data

    return _extractor
