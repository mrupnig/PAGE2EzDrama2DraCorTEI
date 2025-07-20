import xml.etree.ElementTree as ET
import statistics
import os
from collections import defaultdict

# Namespace definieren
ns = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}

# Mapping für Region-Typ zu Präfix
type_prefix = {
    "header": "#",
    "heading": "##",
    "credit": "@",
    "signature-mark": "$",
    "TOC-entry": "",
    "paragraph": "",
    "catch-word": "^"
}

def extract_lines(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    lines_data = []

    for region in root.findall('.//pc:TextRegion', ns):
        region_type = region.attrib.get("type", "")
        prefix = type_prefix.get(region_type, "")

        for line in region.findall('pc:TextLine', ns):
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
                text_equiv = text_equivs[-1]  # fallback

            if text_equiv is not None:
                text = text_equiv.find('pc:Unicode', ns)
                if text is not None and text.text:
                    formatted_text = f"{prefix}{text.text}" if prefix else text.text
                    lines_data.append((y_center, x_min, formatted_text))

    return lines_data

def process_file(filepath, speaker_list):
    lines_data = extract_lines(filepath)

    ys_sorted = sorted(set(y for y, x, t in lines_data))
    line_gaps = [ys_sorted[i+1] - ys_sorted[i] for i in range(len(ys_sorted)-1)]
    avg_gap = statistics.median(line_gaps) if line_gaps else 0
    threshold = avg_gap * 0.5

    line_groups = defaultdict(list)
    group_keys = []

    lines_data.sort(key=lambda tup: (round(tup[0] / 5) * 5, tup[1]))

    for y, x, text in lines_data:
        candidates = [gy for gy in group_keys if abs(y - gy) <= threshold]

        if candidates:
            closest_gy = min(candidates, key=lambda gy: abs(y - gy))
            line_groups[closest_gy].append((x, text))
        else:
            line_groups[y].append((x, text))
            group_keys.append(y)

    output_lines = []
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

def page2ezdrama(data_dir, output_dir, output_filename, all_metadata, speaker_list):
    """
    Konvertiert PAGE-XML-Dateien aus data_dir zu ezdrama-Gesamtausgabe.
    Speichert in output_dir/output_filename.
    
    Parameter:
        data_dir (str): Ordner mit PAGE XML
        output_dir (str): Zielordner
        output_filename (str): Ausgabedateiname
        all_metadata (str): Metadatenblock als String
        speaker_list (List[str]): Liste von Sprechern
    """
    os.makedirs(output_dir, exist_ok=True)
    gesamttext_path = os.path.join(output_dir, output_filename)

    gesamt_output = []

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
