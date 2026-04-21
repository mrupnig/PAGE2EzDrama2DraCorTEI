import xml.etree.ElementTree as ET
import statistics
import os
from collections import defaultdict

try:
    from modules.config import (
        PAGE_XML_NS as ns,
        REGION_TYPE_PREFIX as type_prefix,
        LINE_GROUP_THRESHOLD_FACTOR,
    )
except ImportError:
    from config import (
        PAGE_XML_NS as ns,
        REGION_TYPE_PREFIX as type_prefix,
        LINE_GROUP_THRESHOLD_FACTOR,
    )


def extract_lines(filepath: str) -> list[tuple[float, int, str]]:
    tree = ET.parse(filepath)
    root = tree.getroot()
    lines_data: list[tuple[float, int, str]] = []
    first_toc_done = False

    for region in root.findall('.//pc:TextRegion', ns):
        region_type = region.attrib.get("type", "")
        prefix = type_prefix.get(region_type, "")

        region_lines = region.findall('pc:TextLine', ns)
        n = len(region_lines)

        for i, line in enumerate(region_lines):
            coords_el = line.find('pc:Coords', ns)
            if coords_el is None:
                continue
            points = coords_el.attrib['points']
            coords = [tuple(map(int, pt.split(','))) for pt in points.strip().split()]
            xs = [x for x, y in coords]
            ys = [y for x, y in coords]
            x_min = min(xs)
            y_center = sum(ys) / len(ys)

            text_equivs = line.findall('pc:TextEquiv', ns)
            text_equiv = None
            for te in text_equivs:
                if te.attrib.get('index') == '0':
                    text_equiv = te
                    break
            if text_equiv is None and text_equivs:
                text_equiv = text_equivs[-1]

            if text_equiv is None:
                continue
            uni = text_equiv.find('pc:Unicode', ns)
            if uni is None or not (uni.text and uni.text.strip()):
                continue
            base = uni.text

            # --- Speziallogik ---
            if region_type == "caption":
                if n == 1:
                    formatted_text = f"({base})"
                else:
                    if i == 0:
                        formatted_text = f"({base}"
                    elif i == n - 1:
                        formatted_text = f"{base})"
                    else:
                        formatted_text = base
            elif region_type == "TOC-entry":
                if not first_toc_done:
                    formatted_text = f"~{prefix}{base}" if prefix else f"~{base}"
                    first_toc_done = True
                else:
                    formatted_text = f"{prefix}{base}" if prefix else base
            else:
                formatted_text = f"{prefix}{base}" if prefix else base

            lines_data.append((y_center, x_min, formatted_text))

    return lines_data


def process_file(filepath: str, speaker_list: list[str]) -> list[str]:
    lines_data = extract_lines(filepath)

    ys_sorted = sorted(set(y for y, x, t in lines_data))
    line_gaps = [ys_sorted[i+1] - ys_sorted[i] for i in range(len(ys_sorted)-1)]
    avg_gap = statistics.median(line_gaps) if line_gaps else 0
    threshold = avg_gap * LINE_GROUP_THRESHOLD_FACTOR

    line_groups: dict[float, list[tuple[int, str]]] = defaultdict(list)
    group_keys: list[float] = []

    lines_data.sort(key=lambda tup: (round(tup[0] / 5) * 5, tup[1]))

    for y, x, text in lines_data:
        candidates = [gy for gy in group_keys if abs(y - gy) <= threshold]

        if candidates:
            closest_gy = min(candidates, key=lambda gy: abs(y - gy))
            line_groups[closest_gy].append((x, text))
        else:
            line_groups[y].append((x, text))
            group_keys.append(y)

    output_lines: list[str] = []
    for gy in sorted(line_groups):
        paragraph_lines = [text for _, text in sorted(line_groups[gy])]

        for line in paragraph_lines:
            for name in speaker_list:
                if line.strip().startswith(name):
                    idx = line.find(name) + len(name)
                    line = f"@{line[:idx]}\n{line[idx:].lstrip()}"
                    break
            output_lines.append(line)

    return output_lines


def page2ezdrama(
    data_dir: str,
    output_dir: str,
    output_filename: str,
    all_metadata: str,
    speaker_list: list[str],
) -> str:
    """Konvertiert PAGE-XML-Dateien aus data_dir zu ezdrama-Gesamtausgabe und speichert in output_dir/output_filename."""
    os.makedirs(output_dir, exist_ok=True)
    gesamttext_path = os.path.join(output_dir, output_filename)

    gesamt_output: list[str] = []

    for filename in sorted(os.listdir(data_dir)):
        if filename.endswith(".xml"):
            filepath = os.path.join(data_dir, filename)
            gesamt_output.extend(process_file(filepath, speaker_list))

    with open(gesamttext_path, "w", encoding="utf-8") as f:
        f.write(f"{all_metadata.strip()}\n\n")
        for line in gesamt_output:
            f.write(line + "\n")

    print(f"Fertig. Gesamtausgabe gespeichert in: {gesamttext_path}")
    return gesamttext_path


# Optional zum Testen direkt:
if __name__ == "__main__":
    print("Dieses Modul ist zum Import gedacht. Zum Testen kann hier ein Aufruf integriert werden.")
