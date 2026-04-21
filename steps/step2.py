import os
import re

import streamlit as st

from steps.utils import render_file_editor

FILE_IN  = "output/1_drama_preprocessed.txt"
FILE_OUT = "output/2_drama_speaker_fixed.txt"
SECTION_ID = "sec2"


def render() -> None:
    st.markdown("---")
    st.header("2️⃣ Übersehene Speaker finden")

    if "speaker_line_selection" not in st.session_state:
        st.session_state.speaker_line_selection = {}

    if st.button("Übersehene Speaker suchen"):
        if not os.path.exists(FILE_IN):
            st.error(f"Eingabedatei nicht gefunden: {FILE_IN} — bitte zuerst Schritt 1 ausführen.")
            return
        with open(FILE_IN, "r", encoding="utf-8") as f:
            lines = f.readlines()

        speaker_pattern = re.compile(r"^@(.*)\.$")
        speakers: set[str] = set()
        for line in lines:
            m = speaker_pattern.match(line.strip())
            if m:
                speakers.add(m.group(1))

        found_lines: list[tuple[int, str, str]] = []
        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            for speaker in speakers:
                if line_stripped.startswith(speaker + " ") or line_stripped == speaker:
                    found_lines.append((idx, speaker, line.rstrip("\n")))
                    break

        if found_lines:
            st.session_state.found_lines = found_lines
            st.success(
                f"{len(found_lines)} potenzielle Zeilen gefunden. "
                "Bitte auswählen, welche umgeschrieben werden sollen."
            )
        else:
            st.info("Keine passenden Zeilen gefunden.")

    if "found_lines" in st.session_state:
        with st.form("speaker_correction_form"):
            st.write("### Gefundene Zeilen zur Prüfung und Auswahl")
            for idx, speaker, line in st.session_state.found_lines:
                highlighted_line = line.replace(speaker, f"***{speaker}***", 1)
                st.session_state.speaker_line_selection[idx] = st.checkbox(
                    f"{highlighted_line}", key=f"chk_{idx}", value=False
                )
            submitted = st.form_submit_button("Ausgewählte Zeilen umschreiben und speichern")

        if submitted:
            if not os.path.exists(FILE_IN):
                st.error(f"Eingabedatei nicht gefunden: {FILE_IN}")
                return
            with open(FILE_IN, "r", encoding="utf-8") as f:
                lines = f.readlines()

            speaker_pattern = re.compile(r"^@(.*)\.$")
            speakers = set()
            for line in lines:
                m = speaker_pattern.match(line.strip())
                if m:
                    speakers.add(m.group(1))

            processed_lines: list[str] = []
            i = 0
            while i < len(lines):
                line = lines[i].rstrip("\n")
                line_stripped = line.strip()
                matched = False
                for speaker in speakers:
                    if (
                        (line_stripped.startswith(speaker + " ") or line_stripped == speaker)
                        and st.session_state.speaker_line_selection.get(i, False)
                    ):
                        rest = line_stripped[len(speaker):].lstrip()
                        processed_lines.append(f"@{speaker}.")
                        if rest:
                            processed_lines.append(rest)
                        matched = True
                        break
                if not matched:
                    processed_lines.append(line)
                i += 1

            with open(FILE_OUT, "w", encoding="utf-8") as f:
                for pline in processed_lines:
                    f.write(pline + "\n")

            st.success(f"Ausgewählte Zeilen wurden umgeschrieben und gespeichert unter: {FILE_OUT}")
            st.session_state.current_edit_path = FILE_OUT
            st.session_state.editor_section    = SECTION_ID
            st.rerun()

    st.divider()
    st.subheader("Datei direkt in der App bearbeiten")
    render_file_editor(SECTION_ID)
