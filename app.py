import streamlit as st
import re
from collections import defaultdict
from modules.GetSpeakers import *
from modules.PAGE2EzDrama import *
from modules.DraCorParser import Parser
import math


st.title("PAGE to EzDrama to DraCorTEI")
st.text("""
        Mit dieser Anwendung können Dramen von PAGE biszu DraCor TEI konvertiert werden.
""")

st.header("1️⃣ Preprocessing", anchor="preprocessing")

st.write("### Datenordner auswählen")

data = st.text_input("Pfad zum Datenordner", value="/home/martin/ocr4all/data/Iffland_Elise_von_Valberg/processing")

title = st.text_input("Titel des Dramas", value="Marianne oder der Sieg der Tugend")
subtitle = st.text_input("Untertitel des Dramas", value="ein rührendes Lustspiel in 3 Aufzügen")
author = st.text_input("Autor des Dramas", value="Victoria Rupp")

all_metadata = f"""
@title {title}
@subtitle {subtitle}
@author {author}
"""

if st.button("Preprocessing jetzt starten"):
    with st.spinner("Extrahiere und bereite Daten vor..."):
        dramatis_personae = extract_toc_entries(data)
        speaker_list_raw, speaker_examples = extract_sentences_with_dot_and_limit(data)
        figuren = extract_figuren(dramatis_personae)
        st.session_state.dramatis_personae = dramatis_personae
        st.session_state.speaker_list_raw = speaker_list_raw
        st.session_state.speaker_examples = speaker_examples
        st.session_state.figuren = figuren
    st.success("Preprocessing abgeschlossen.")

if 'speaker_list_raw' in st.session_state:
    st.write(f"**Extrahierte Figuren:** {st.session_state.dramatis_personae}")
    st.write(f"**Bereinigte Figuren aus TOC:** {st.session_state.figuren}")

    st.write("### Interaktive Validierung der Sprecher")

    if 'speaker_selection' not in st.session_state:
        st.session_state.speaker_selection = {speaker: False for speaker in st.session_state.speaker_list_raw}

    with st.form("speaker_validation_form"):
        for speaker in sorted(st.session_state.speaker_list_raw):
            match, score = compute_similarity(speaker, st.session_state.figuren)
            cleaned_speaker = re.sub(r'[^\w\s]', '', speaker).strip().lower()

            # Beispielzeile suchen
            example = st.session_state.speaker_examples.get(cleaned_speaker)
            if example is None:
                for token in cleaned_speaker.split():
                    example = st.session_state.speaker_examples.get(token)
                    if example:
                        break
            if example is None:
                example = "(kein Beispiel verfügbar)"

            # Anzahl passender Beispielsätze zählen
            example_count = sum(
                1 for key in st.session_state.speaker_examples.keys()
                if cleaned_speaker in key or any(token in key for token in cleaned_speaker.split())
            )

            color = "#ffcccc" if score < 0.5 else "#fff2cc" if score < 0.75 else "#ccffcc"

            cols = st.columns([3, 1])

            with cols[0]:
                st.markdown(f"""
                    <div style='background-color: {color}; padding: 10px; border-radius: 5px;'>
                        <p style='margin: 0'><strong>{speaker}</strong> ({example_count} Matches: {match}, Score: {score:.3f})</p>
                        <p style='margin: 0'><em>Beispiel:</em> {example}</p>
                    </div>
                """, unsafe_allow_html=True)

            with cols[1]:
                st.session_state.speaker_selection[speaker] = st.checkbox("", key=f"chk_{speaker}", value=st.session_state.speaker_selection[speaker])

        submitted = st.form_submit_button("Textdatei mit gewählten Sprechern erstellen")


    if submitted:
        valid_speakers = [speaker for speaker, keep in st.session_state.speaker_selection.items() if keep]
        if valid_speakers:
            output_path = page2ezdrama(
                data_dir=data,
                output_dir="output",
                output_filename="1_drama_preprocessed.txt",
                all_metadata=all_metadata,
                speaker_list=valid_speakers
            )
            st.success(f"Gesamtausgabe gespeichert unter: {output_path}")
        else:
            st.warning("Bitte mindestens einen Sprecher auswählen, bevor die Datei erstellt wird.")

st.markdown("---")

st.header("1️⃣.2️⃣ Übersehene Speaker finden")

file_path = "output/1_drama_preprocessed.txt"
output_path = "output/1_2_drama_processed.txt"

if 'speaker_line_selection' not in st.session_state:
    st.session_state.speaker_line_selection = {}

if st.button("Übersehene Speaker suchen"):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    speaker_pattern = re.compile(r"^@(.*)\.$")
    speakers = set()
    for line in lines:
        match = speaker_pattern.match(line.strip())
        if match:
            speakers.add(match.group(1))

    found_lines = []
    for idx, line in enumerate(lines):
        line_stripped = line.strip()
        for speaker in speakers:
            if line_stripped.startswith(speaker + " ") or line_stripped == speaker:
                found_lines.append((idx, speaker, line.rstrip("\n")))
                break

    if found_lines:
        st.session_state.found_lines = found_lines
        st.success(f"{len(found_lines)} potenzielle Zeilen gefunden. Bitte auswählen, welche umgeschrieben werden sollen.")
    else:
        st.info("Keine passenden Zeilen gefunden.")

if 'found_lines' in st.session_state:
    with st.form("speaker_correction_form"):
        st.write("### Gefundene Zeilen zur Prüfung und Auswahl")
        for idx, speaker, line in st.session_state.found_lines:
            highlighted_line = line.replace(speaker, f"***{speaker}***", 1)
            st.session_state.speaker_line_selection[idx] = st.checkbox(
                f"{highlighted_line}",
                key=f"chk_{idx}",
                value=False
            )
        submitted = st.form_submit_button("Ausgewählte Zeilen umschreiben und speichern")

    if submitted:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        speaker_pattern = re.compile(r"^@(.*)\.$")
        speakers = set()
        for line in lines:
            match = speaker_pattern.match(line.strip())
            if match:
                speakers.add(match.group(1))

        processed_lines = []
        i = 0
        while i < len(lines):
            line = lines[i].rstrip("\n")
            line_stripped = line.strip()

            matched = False
            for speaker in speakers:
                if (line_stripped.startswith(speaker + " ") or line_stripped == speaker) and st.session_state.speaker_line_selection.get(i, False):
                    rest = line_stripped[len(speaker):].lstrip()
                    processed_lines.append(f"@{speaker}.")
                    if rest:
                        processed_lines.append(rest)
                    matched = True
                    break

            if not matched:
                processed_lines.append(line)

            i += 1

        with open(output_path, "w", encoding="utf-8") as f:
            for pline in processed_lines:
                f.write(pline + "\n")

        st.success(f"Ausgewählte Zeilen wurden umgeschrieben und gespeichert unter: {output_path}")


st.markdown("---")
st.header("1️⃣.3️⃣ Klammer-Zeilen extrahieren")


file_path = "output/1_2_drama_processed.txt"
output_path = "output/1_3_drama_processed_brackets_fixed.txt"

if 'editable_bracket_contents' not in st.session_state:
    st.session_state.editable_bracket_contents = []

if st.button("Klammer-Inhalte extrahieren"):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Klammern-Inhalte robust extrahieren (inkl. Zeilenumbrüche)
    bracket_contents = re.findall(r"(?s)(\(.*?\))", text)

    if bracket_contents:
        st.session_state.editable_bracket_contents = bracket_contents
        st.success(f"{len(bracket_contents)} Klammer-Inhalte erfolgreich extrahiert. Jetzt bearbeitbar.")
    else:
        st.info("Keine Klammer-Inhalte gefunden.")

if st.session_state.get('editable_bracket_contents'):
    st.write("### Gefundene Klammer-Inhalte zur Bearbeitung")
    updated_contents = []
    for idx, content in enumerate(st.session_state.editable_bracket_contents):
        edited = st.text_area(f"Fund {idx+1}", value=content.strip(), height=80)
        updated_contents.append(edited)

    if st.button("Änderungen übernehmen und speichern"):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        # Alle alten Klammerinhalte durch die neuen ersetzen
        def replacement_generator():
            for new_content in updated_contents:
                yield new_content
        replacer = replacement_generator()

        def replace_match(match):
            return next(replacer)

        new_text = re.sub(r"(?s)(\(.*?\))", replace_match, text, count=len(updated_contents))

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(new_text)

        st.success(f"Alle Änderungen wurden übernommen und gespeichert unter: {output_path}")

st.markdown("---")
st.header("2️⃣ Interaktive Speaker-Normalisierung")

# Load text
# Button zum Laden der Datei, um automatisches Laden zu verhindern
if st.button("Textdatei laden"):
    with open("output/1_3_drama_processed_brackets_fixed.txt", "r", encoding="utf-8") as f:
        text = f.read()
    st.session_state.text_loaded = True
    st.session_state.text_content = text
    st.success("Datei erfolgreich geladen.")

if st.session_state.get('text_loaded', False):
    text = st.session_state.text_content
    speakers_raw = re.findall(r"^@(.*?)$", text, re.MULTILINE)
    unique_speakers = sorted(set(speakers_raw))

    st.subheader("Detected Speakers")
    st.write(f"Total speakers detected: {len(unique_speakers)}")

    if 'speaker_groups' not in st.session_state:
        st.session_state.speaker_groups = defaultdict(list)
    if 'remaining_speakers' not in st.session_state:
        st.session_state.remaining_speakers = unique_speakers.copy()

    raw_group_name = st.text_input("Add a new normalized speaker (only name, e.g., Klingbeil)")
    if st.button("Add Speaker Group"):
        if raw_group_name:
            formatted_group_name = f"@{raw_group_name.strip()}."
            if formatted_group_name not in st.session_state.speaker_groups:
                # Neu angelegte Speaker an den Anfang der OrderedDict-ähnlichen Struktur setzen
                st.session_state.speaker_groups = defaultdict(list, {formatted_group_name: []} | st.session_state.speaker_groups)
                st.success(f"Added new group: {formatted_group_name}")
            else:
                st.warning(f"Group {formatted_group_name} already exists.")

    left_col, right_col = st.columns(2)

    with left_col:
        if st.session_state.remaining_speakers:
            st.subheader("Speakers Remaining for Assignment")
            st.write(st.session_state.remaining_speakers)
        else:
            st.success("All speakers have been assigned to a group.")

    with right_col:
        st.subheader("Assign Speakers to Normalized Groups")
        for group_name in list(st.session_state.speaker_groups.keys()):
            st.write(f"### {group_name}")
            selected = st.multiselect(f"Select speakers to add to {group_name}", st.session_state.remaining_speakers, key=f"select_{group_name}")
            if st.button(f"Add to {group_name}", key=f"add_{group_name}"):
                for sel in selected:
                    st.session_state.speaker_groups[group_name].append(sel)
                    st.session_state.remaining_speakers.remove(sel)
                st.success(f"Added {len(selected)} speaker(s) to {group_name}")

    if st.button("Normalize and Save File"):
        normalized_text = text
        for group_name, variants in st.session_state.speaker_groups.items():
            for variant in variants:
                pattern = r"^@" + re.escape(variant) + r"$"
                normalized_text = re.sub(pattern, group_name, normalized_text, flags=re.MULTILINE)
        with open("output/2_normalized_speakers.txt", "w", encoding="utf-8") as f_out:
            f_out.write(normalized_text)
        st.success("File normalized and saved to 'output/2_normalized_speakers.txt'")

st.markdown("---")

# Neuer Abschnitt zum Bereinigen des Gesamttexts
st.header("3️⃣ Gesamttext bereinigen")

if st.button("Gesamttext bereinigen"):
    file_path = "output/2_normalized_speakers.txt"
    output_path = "output/3_drama_clean.txt"

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cleaned_lines = []
    buffer = ""
    verse_mode = False

    def process_line(line):
        line = line.rstrip()
        if line.endswith("-") and not line.endswith(" -") and not line.endswith("--"):
            return line[:-1], True
        return line, False

    def normalize_text(text):
        replacements = {
            "ſ": "s",
            "ʒ": "z",
            "Ʒ": "Z",
            "aͤ": "ä",
            "oͤ": "ö",
            "uͤ": "ü",
            "Jch": "Ich",
            "Jtzt": "Itzt",
            "Jst": "Ist",
            "Jn": "In",
            "Jm": "Im",
            "Jhm": "Ihm",
            "Jhn": "Ihn",
            "Jhr": "Ihr",
            "Jr": "Ir"
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if line.startswith("~"):
            verse_mode = True
            if buffer:
                cleaned_lines.append(buffer.strip())
                buffer = ""
            cleaned_lines.append(normalize_text(line.strip()))
            i += 1
            continue

        if verse_mode:
            if not line.startswith(("@", "#", "^", "$", "~", "(")):
                cleaned_lines.append(normalize_text(line.strip()))
                i += 1
                continue
            else:
                verse_mode = False

        if line.startswith("@"):
            verse_mode = False
            if buffer:
                cleaned_lines.append(buffer.strip())
                buffer = ""
            speaker_line = line
            i += 1
            if i < len(lines):
                next_line = lines[i].strip()
                if next_line.startswith("(") and next_line.endswith(")"):
                    speaker_line += f" {next_line}"
                    i += 1
            cleaned_lines.append(speaker_line)
            continue

        if line.startswith("$"):
            verse_mode = False
            combined_line, is_hyphenated = process_line(line[1:].strip())
            i += 1
            while i < len(lines) and lines[i].strip().startswith("$"):
                next_line_content = lines[i].strip()[1:].strip()
                processed_next, next_is_hyphenated = process_line(next_line_content)
                if is_hyphenated:
                    combined_line += processed_next
                else:
                    combined_line += " " + processed_next
                is_hyphenated = next_is_hyphenated
                i += 1
            if buffer:
                cleaned_lines.append(buffer.strip())
                buffer = ""
            cleaned_lines.append("$" + combined_line.strip())
            continue

        if line.startswith(("#", "^")):
            verse_mode = False
            if buffer:
                cleaned_lines.append(buffer.strip())
                buffer = ""
            cleaned_lines.append(line)
            i += 1
            continue

        processed_line, is_hyphenated = process_line(line)
        buffer += " " + processed_line

        while is_hyphenated and i + 1 < len(lines):
            i += 1
            next_line = lines[i].strip()
            processed_line, is_hyphenated = process_line(next_line)
            buffer += processed_line

        i += 1

    if buffer:
        cleaned_lines.append(buffer.strip())

    cleaned_lines = [normalize_text(line) for line in cleaned_lines]

    with open(output_path, "w", encoding="utf-8") as f:
        for line in cleaned_lines:
            f.write(line + "\n")

    st.success(f"Bereinigter Text gespeichert unter: {output_path}")

st.markdown("---")

# Abschnitt: EzDrama to DraCor-TEI
st.header("4️⃣ EzDrama zu DraCor-TEI konvertieren")

# Konfiguration der Parser-Optionen direkt oben in der App
bracketstages = st.checkbox("Klammern als Bühnenanweisungen behandeln (bracketstages)", value=True)
is_prose = st.checkbox("Prosa-Modus aktivieren (is_prose)", value=True)
dracor_id = st.text_input("Dracor ID", value="Z251577604")
dracor_lang = st.text_input("Sprache des Dramas (dracor_lang)", value="de")

if st.button("EzDrama to DraCor-TEI"):
    with st.spinner("Konvertiere EzDrama zu DraCor-TEI..."):
        parser = Parser(
            bracketstages=bracketstages,
            is_prose=is_prose,
            dracor_id=dracor_id,
            dracor_lang=dracor_lang
        )
        parser.process_file("output/3_drama_clean.txt")
        st.success(f"Konvertierung abgeschlossen: {parser.outputname}")