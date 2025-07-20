import os
import xml.etree.ElementTree as ET
import re
import difflib
from collections import defaultdict

ns = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}

type_prefix = {
    # Falls nötig, hier Typen mit Präfixen eintragen
}

def extract_lines(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    lines_data = []

    for region in root.findall('.//pc:TextRegion', ns):
        region_type = region.attrib.get("type", "")
        prefix = type_prefix.get(region_type, "")
        if region_type != "paragraph":
            continue  # Nur paragraph-Regionen verarbeiten

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
                text_equiv = text_equivs[-1]

            if text_equiv is not None:
                text = text_equiv.find('pc:Unicode', ns)
                if text is not None and text.text:
                    formatted_text = f"{prefix}{text.text}" if prefix else text.text
                    lines_data.append((y_center, x_min, formatted_text))

    return lines_data

def extract_sentences_with_dot_and_limit(directory):
    extracted_sentences = set()
    speaker_examples = {}

    for filename in os.listdir(directory):
        if filename.endswith(".xml"):
            filepath = os.path.join(directory, filename)
            lines = extract_lines(filepath)

            for _, _, text in lines:
                clean_text = text.lstrip("#@$^").strip()
                if not clean_text or not (clean_text[0].isupper() or re.match(r'^[vV](\.|\s|,|;)\s*', clean_text)):
                    continue

                # Indizes aller Punkte in den ersten 13 Zeichen sammeln
                dot_indices = [m.start() for m in re.finditer(r'\.', clean_text) if m.start() <= 13]

                if dot_indices:
                    # Bis zu drei Punkte berücksichtigen
                    for i in range(min(3, len(dot_indices))):
                        end_pos = dot_indices[i]
                        sentence = clean_text[:end_pos + 1].strip()
                        extracted_sentences.add(sentence)

                        # Speichere den *gesamten* clean_text als Beispiel
                        cleaned_sentence = re.sub(r'[^\w\s]', '', sentence).strip().lower()
                        if cleaned_sentence not in speaker_examples:
                            speaker_examples[cleaned_sentence] = clean_text

    return extracted_sentences, speaker_examples





def extract_figuren(dramatis_personae: str):
    """
    Extrahiert Figuren aus einer dramatis personae Liste als Menge bereinigter Namen,
    wobei maximal die ersten 3 Wörter pro Zeile berücksichtigt werden.
    """
    figuren = set()

    for line in dramatis_personae.splitlines():
        line = line.strip()
        if not line or line.startswith("^"):
            continue

        # Besitzformen entfernen
        line = re.sub(r"['‘’`´]s\b", "", line)

        # Nur die ersten 3 Wörter behalten
        words = line.split()
        first_words = " ".join(words[:3])

        # Split by commas
        parts = [p.strip() for p in re.split(r",|\n", first_words) if p.strip()]
        for p in parts:
            if re.search(r'[A-Za-zÄÖÜäöüß]', p):
                # Titel entfernen
                #p_clean = re.sub(r'^(Graf|Ritter|Fräulein|Gräfin)\s+', '', p, flags=re.IGNORECASE)
                # Namenszusätze "von ..." entfernen
                p_clean = re.sub(r'\s+von.*$', '', p, flags=re.IGNORECASE)
                p_clean = p_clean.strip()
                figuren.add(p_clean)

    # Zeichen bereinigen, Normalisierung und Kleinbuchstaben
    figuren = {
        re.sub(r'[^\w\s]', '', f).replace('ſ', 's').strip().lower()
        for f in figuren if f
    }

    return figuren

def compute_similarity(word, figuren):
    """
    Berechnet die ähnlichste Figur zu 'word' aus der Menge 'figuren' und gibt (match, score) zurück.
    """
    best_match = None
    best_score = 0.0
    word_clean = re.sub(r'[^\w\s]', '', word).strip().lower()
    tokens = word_clean.split()

    for token in tokens:
        for figur in figuren:
            score = difflib.SequenceMatcher(None, token, figur).ratio()
            if token == figur:
                return figur, 1.0
            if score > best_score or (
                score == best_score and abs(len(token) - len(figur)) < abs(len(token) - len(best_match) if best_match else 100)
            ):
                best_score = score
                best_match = figur

    return best_match, best_score


def filter_valid_speakers(speaker_list, figuren, speaker_examples=None, interactive=True):
    """
    Filtert valide Sprecher aus speaker_list basierend auf figuren.
    Zeigt bei interactive=True eine Beispielzeile VOR der Entscheidung an.
    """
    valid_speakers = []

    if interactive:
        print("Drücke 'j' für JA (Speaker behalten), 'n' für NEIN (entfernen):\n")

    for w in speaker_list:
        match, score = compute_similarity(w, figuren)

        if score > 0.75:
            status = "wahrscheinlich Figur"
        elif score > 0.5:
            status = "vielleicht Figur"
        else:
            status = "keine Figur"

        print(f"\n'{w}' erkannt als -> '{match if match else '---'}' ({status}, Score: {score:.3f})")

        # Beispielzeile VOR der Entscheidung anzeigen:
        if speaker_examples is not None:
            cleaned_w = re.sub(r'[^\w\s]', '', w).strip().lower()
            example_line = speaker_examples.get(cleaned_w)

            if example_line is None:
                for token in cleaned_w.split():
                    example_line = speaker_examples.get(token)
                    if example_line:
                        break

            if example_line is None:
                example_line = "(keine Zeile gefunden)"

            # Zähle alle passenden Beispielsätze
            example_count = 0
            for key in speaker_examples.keys():
                if cleaned_w in key or any(token in key for token in cleaned_w.split()):
                    example_count += 1

            print(f"eine von {example_count} Beispielzeilen: {example_line}")

        keep = False
        if interactive:
            while True:
                user_input = input("Behalten? (j/n): ").strip().lower()
                if user_input in ['j', 'n']:
                    break
                else:
                    print("Bitte 'j' oder 'n' eingeben.")
            keep = user_input == 'j'
        else:
            keep = score > 0.5

        if keep:
            valid_speakers.append(w)

    return valid_speakers

def extract_toc_entries(folder_path):
    """
    Extrahiert den Text aller <TextLine>-Elemente innerhalb von <TextRegion type="TOC-entry">
    aus allen PAGE XML-Dateien im angegebenen Ordner.

    Rückgabe:
        str: Alle extrahierten Zeilen, durch Zeilenumbrüche getrennt, als ein einziger String.
    """
    ns = {'pc': 'http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15'}
    lines_text = []

    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.xml'):
            filepath = os.path.join(folder_path, filename)
            tree = ET.parse(filepath)
            root = tree.getroot()

            for region in root.findall('.//pc:TextRegion[@type="TOC-entry"]', ns):
                for line in region.findall('pc:TextLine', ns):
                    text_equivs = line.findall('pc:TextEquiv', ns)
                    text_equiv = None

                    # Bevorzugt index="0", sonst den letzten vorhandenen
                    for te in text_equivs:
                        if te.attrib.get('index') == '0':
                            text_equiv = te
                            break
                    if text_equiv is None and text_equivs:
                        text_equiv = text_equivs[-1]

                    if text_equiv is not None:
                        text_el = text_equiv.find('pc:Unicode', ns)
                        if text_el is not None and text_el.text:
                            lines_text.append(text_el.text.strip())

    return "\n".join(lines_text)
