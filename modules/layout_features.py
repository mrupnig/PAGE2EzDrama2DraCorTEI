"""Extraktion von Layout-Features (Koordinaten, RegionTypes) aus dem
hand-annotierten PAGE-XML-Korpus unter ``pagetypes/`` für die explorativen
Notebooks (``notebooks/explore_pagetypes.ipynb``, ``notebooks/explore_regiontypes.ipynb``)
und für eine spätere automatische PageType-/RegionType-Klassifikation.
"""

from __future__ import annotations

import hashlib
import random
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

try:
    from modules.config import PAGE_XML_NS as ns
except ImportError:
    from config import PAGE_XML_NS as ns

# Wurzel des explorativen Korpus. Unabhängig vom App-BASE_DIR (modules/paths.py),
# da pagetypes/ ein statisches, manuell kuratiertes Trainings-/Referenzkorpus ist.
PAGETYPES_DIR: Path = Path(__file__).resolve().parent.parent / "pagetypes"

# Kategorien mit flacher Struktur: 1 XML-Datei pro Werk.
FLAT_CATEGORIES: tuple[str, ...] = ("title_page", "personae_dramatis")

# Kategorien mit einem Unterordner je Werk, der viele Seiten-XMLs enthält.
NESTED_CATEGORIES: tuple[str, ...] = ("drama", "libretti")

CATEGORIES: tuple[str, ...] = FLAT_CATEGORIES + NESTED_CATEGORIES

CACHE_DIR: Path = Path(__file__).resolve().parent.parent / "notebooks" / "cache"


@dataclass(frozen=True)
class PageRef:
    """Verweis auf eine einzelne PAGE-XML-Seite im Korpus."""

    page_type: str
    work_id: str
    path: Path


@dataclass
class GlyphRecord:
    glyph_id: str
    x: float
    y: float


@dataclass
class WordRecord:
    word_id: str
    glyphs: list[GlyphRecord] = field(default_factory=list)


@dataclass
class LineRecord:
    line_id: str
    words: list[WordRecord] = field(default_factory=list)


@dataclass
class RegionRecord:
    region_id: str
    region_type: str | None  # None = kein `type`-Attribut vorhanden
    x_min: float
    y_min: float
    x_max: float
    y_max: float
    lines: list[LineRecord] = field(default_factory=list)


@dataclass
class PageRecord:
    page_ref: PageRef
    page_width: int
    page_height: int
    regions: list[RegionRecord] = field(default_factory=list)


def iter_page_files(category: str) -> list[PageRef]:
    """Listet alle Seiten-Dateien einer Kategorie auf.

    Kapselt den strukturellen Unterschied zwischen flachen Kategorien
    (1 Datei = 1 Werk) und verschachtelten Kategorien (1 Unterordner je Werk
    mit vielen Seiten).
    """
    if category not in CATEGORIES:
        raise ValueError(f"Unbekannte Kategorie '{category}'. Erwartet: {CATEGORIES}")

    category_dir = PAGETYPES_DIR / category
    refs: list[PageRef] = []

    if category in FLAT_CATEGORIES:
        for path in sorted(category_dir.glob("*.xml")):
            work_id = path.stem
            refs.append(PageRef(page_type=category, work_id=work_id, path=path))
    else:
        for work_dir in sorted(p for p in category_dir.iterdir() if p.is_dir()):
            for path in sorted(work_dir.glob("*.xml")):
                refs.append(PageRef(page_type=category, work_id=work_dir.name, path=path))

    return refs


def sample_pages(
    category: str,
    n_works: int | None = None,
    max_pages_per_work: int | None = None,
    seed: int = 42,
) -> list[PageRef]:
    """Zieht eine Stichprobe von Seiten, werkbasiert (siehe Konzept in dev/DEV-explore_nb.md).

    Erst wird eine Stichprobe von Werken gezogen (``n_works``), danach je Werk
    maximal ``max_pages_per_work`` Seiten zufällig ausgewählt. Bei flachen
    Kategorien (title_page, personae_dramatis) entspricht ein Werk bereits
    einer Seite, dort werden beide Parameter ignoriert und alle Dateien
    verwendet.
    """
    rng = random.Random(seed)
    all_refs = iter_page_files(category)

    if category in FLAT_CATEGORIES:
        return all_refs

    by_work: dict[str, list[PageRef]] = {}
    for ref in all_refs:
        by_work.setdefault(ref.work_id, []).append(ref)

    work_ids = sorted(by_work)
    if n_works is not None and n_works < len(work_ids):
        work_ids = rng.sample(work_ids, n_works)

    sampled: list[PageRef] = []
    for work_id in work_ids:
        pages = by_work[work_id]
        if max_pages_per_work is not None and max_pages_per_work < len(pages):
            pages = rng.sample(pages, max_pages_per_work)
        sampled.extend(pages)

    return sampled


def _parse_points(points_str: str) -> list[tuple[float, float]]:
    return [tuple(map(float, pt.split(","))) for pt in points_str.strip().split()]


def _centroid(points_str: str) -> tuple[float, float] | None:
    if not points_str.strip():
        return None
    try:
        coords = _parse_points(points_str)
    except ValueError:
        return None
    xs = [x for x, _ in coords]
    ys = [y for _, y in coords]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _bbox(points_str: str) -> tuple[float, float, float, float] | None:
    if not points_str.strip():
        return None
    try:
        coords = _parse_points(points_str)
    except ValueError:
        return None
    xs = [x for x, _ in coords]
    ys = [y for _, y in coords]
    return min(xs), min(ys), max(xs), max(ys)


def parse_page(page_ref: PageRef) -> PageRecord | None:
    """Parst eine einzelne PAGE-XML-Datei in ein :class:`PageRecord`.

    Gibt ``None`` zurück, wenn die Datei keine ``<Page>``-Element enthält
    (z.B. bei einer leeren, vollautomatisch prozessierten Seite).
    """
    try:
        tree = ET.parse(page_ref.path)
    except ET.ParseError:
        return None
    root = tree.getroot()

    page_el = root.find("pc:Page", ns)
    if page_el is None:
        return None

    page_width = int(page_el.attrib.get("imageWidth", 0))
    page_height = int(page_el.attrib.get("imageHeight", 0))

    regions: list[RegionRecord] = []
    for region_el in page_el.findall("pc:TextRegion", ns):
        region_id = region_el.attrib.get("id", "")
        region_type = region_el.attrib.get("type")  # None, falls nicht vorhanden

        coords_el = region_el.find("pc:Coords", ns)
        bbox = _bbox(coords_el.attrib.get("points", "")) if coords_el is not None else None
        if bbox is None:
            continue
        x_min, y_min, x_max, y_max = bbox

        lines: list[LineRecord] = []
        for line_el in region_el.findall("pc:TextLine", ns):
            line_id = line_el.attrib.get("id", "")
            words: list[WordRecord] = []
            for word_el in line_el.findall("pc:Word", ns):
                word_id = word_el.attrib.get("id", "")
                glyphs: list[GlyphRecord] = []
                for glyph_el in word_el.findall("pc:Glyph", ns):
                    glyph_id = glyph_el.attrib.get("id", "")
                    glyph_coords_el = glyph_el.find("pc:Coords", ns)
                    if glyph_coords_el is None:
                        continue
                    centroid = _centroid(glyph_coords_el.attrib.get("points", ""))
                    if centroid is None:
                        continue
                    x, y = centroid
                    glyphs.append(GlyphRecord(glyph_id=glyph_id, x=x, y=y))
                if glyphs:
                    words.append(WordRecord(word_id=word_id, glyphs=glyphs))
            if words:
                lines.append(LineRecord(line_id=line_id, words=words))

        regions.append(
            RegionRecord(
                region_id=region_id,
                region_type=region_type,
                x_min=x_min,
                y_min=y_min,
                x_max=x_max,
                y_max=y_max,
                lines=lines,
            )
        )

    return PageRecord(page_ref=page_ref, page_width=page_width, page_height=page_height, regions=regions)


def parse_pages(page_refs: list[PageRef]) -> list[PageRecord]:
    records = []
    for ref in page_refs:
        record = parse_page(ref)
        if record is not None and record.page_width and record.page_height:
            records.append(record)
    return records


def to_long_df(records: list[PageRecord], typed_regions_only: bool = False) -> pd.DataFrame:
    """Glyph-Ebene (long format), eine Zeile pro Glyph.

    ``typed_regions_only=True`` verwirft Regionen ohne ``type``-Attribut
    (siehe Konzept: das sind eingebettete Titelseiten innerhalb von
    drama/libretti-Werkordnern, keine echten Dramentext-Regionen).
    """
    rows = []
    for page in records:
        ref = page.page_ref
        for region in page.regions:
            if typed_regions_only and not region.region_type:
                continue
            for line in region.lines:
                for word in line.words:
                    for glyph in word.glyphs:
                        rows.append(
                            {
                                "page_type": ref.page_type,
                                "work_id": ref.work_id,
                                "page_file": ref.path.name,
                                "page_width": page.page_width,
                                "page_height": page.page_height,
                                "region_id": region.region_id,
                                "region_type": region.region_type,
                                "line_id": line.line_id,
                                "word_id": word.word_id,
                                "glyph_id": glyph.glyph_id,
                                "x": glyph.x,
                                "y": glyph.y,
                                "x_norm": glyph.x / page.page_width,
                                "y_norm": glyph.y / page.page_height,
                            }
                        )
    return pd.DataFrame(rows)


def to_region_df(records: list[PageRecord], typed_regions_only: bool = False) -> pd.DataFrame:
    """Region-Ebene (aggregiert), eine Zeile pro Region."""
    rows = []
    for page in records:
        ref = page.page_ref
        for region in page.regions:
            if typed_regions_only and not region.region_type:
                continue
            n_lines = len(region.lines)
            n_words = sum(len(line.words) for line in region.lines)
            n_glyphs = sum(len(word.glyphs) for line in region.lines for word in line.words)
            x_min_norm = region.x_min / page.page_width
            y_min_norm = region.y_min / page.page_height
            x_max_norm = region.x_max / page.page_width
            y_max_norm = region.y_max / page.page_height
            rows.append(
                {
                    "page_type": ref.page_type,
                    "work_id": ref.work_id,
                    "page_file": ref.path.name,
                    "region_id": region.region_id,
                    "region_type": region.region_type,
                    "x_min_norm": x_min_norm,
                    "y_min_norm": y_min_norm,
                    "x_max_norm": x_max_norm,
                    "y_max_norm": y_max_norm,
                    "width_norm": x_max_norm - x_min_norm,
                    "height_norm": y_max_norm - y_min_norm,
                    "area_norm": (x_max_norm - x_min_norm) * (y_max_norm - y_min_norm),
                    "n_lines": n_lines,
                    "n_words": n_words,
                    "n_glyphs": n_glyphs,
                }
            )
    return pd.DataFrame(rows)


def _cache_key(category: str, n_works: int | None, max_pages_per_work: int | None, seed: int) -> str:
    raw = f"{category}-{n_works}-{max_pages_per_work}-{seed}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def build_dataset(
    category: str,
    n_works: int | None = None,
    max_pages_per_work: int | None = None,
    seed: int = 42,
    use_cache: bool = True,
    force_refresh: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Baut Glyph- und Region-DataFrames für eine Kategorie, mit Parquet-Cache.

    Gibt ``(long_df, region_df)`` zurück, jeweils **ungefiltert** (inkl.
    Regionen ohne ``type``). Filterung auf typisierte Regionen erfolgt bei
    Bedarf im Notebook selbst (``df[df.region_type.notna()]``), da beide
    Notebooks unterschiedliche Anforderungen daran haben.
    """
    key = _cache_key(category, n_works, max_pages_per_work, seed)
    long_path = CACHE_DIR / f"{category}_{key}_long.parquet"
    region_path = CACHE_DIR / f"{category}_{key}_region.parquet"

    if use_cache and not force_refresh and long_path.exists() and region_path.exists():
        return pd.read_parquet(long_path), pd.read_parquet(region_path)

    refs = sample_pages(category, n_works=n_works, max_pages_per_work=max_pages_per_work, seed=seed)
    records = parse_pages(refs)
    long_df = to_long_df(records)
    region_df = to_region_df(records)

    if use_cache:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        long_df.to_parquet(long_path)
        region_df.to_parquet(region_path)

    return long_df, region_df
