import os
import re
from collections import defaultdict

import streamlit as st

from steps.utils import render_file_editor

FILE_IN    = "output/3_drama_brackets_fixed.txt"
FILE_OUT   = "output/4_normalized_speakers.txt"
SECTION_ID = "sec4"


def render() -> None:
    st.markdown("---")
    st.header("4️⃣ Interaktive Speaker-Normalisierung")

    if st.button("Textdatei laden"):
        if not os.path.exists(FILE_IN):
            st.error(f"Eingabedatei nicht gefunden: {FILE_IN} — bitte zuerst Schritt 3 ausführen.")
            return
        with open(FILE_IN, "r", encoding="utf-8") as f:
            text = f.read()
        st.session_state.text_loaded  = True
        st.session_state.text_content = text
        st.success("Datei erfolgreich geladen.")

    if st.session_state.get("text_loaded", False):
        text = st.session_state.text_content
        speakers_raw   = re.findall(r"^@(.*?)$", text, re.MULTILINE)
        unique_speakers = sorted(set(speakers_raw))

        st.subheader("Gefundene Sprecher")
        st.write(f"Anzahl gefundener Sprecher: {len(unique_speakers)}")

        if "speaker_groups" not in st.session_state:
            st.session_state.speaker_groups = defaultdict(list)
        if "remaining_speakers" not in st.session_state:
            st.session_state.remaining_speakers = unique_speakers.copy()

        raw_group_name = st.text_input("Einen neuen Sprecher anlegen")
        if st.button("neue Sprechergruppe anlegen"):
            if raw_group_name:
                formatted = f"@{raw_group_name.strip()}."
                if formatted not in st.session_state.speaker_groups:
                    # Neu angelegte Speaker an den Anfang setzen
                    st.session_state.speaker_groups = defaultdict(
                        list, {formatted: []} | st.session_state.speaker_groups
                    )
                    st.success(f"neue Gruppe hinzugefügt: {formatted}")
                else:
                    st.warning(f"Gruppe {formatted} existiert bereits.")

        left_col, right_col = st.columns(2)

        with left_col:
            if st.session_state.remaining_speakers:
                st.subheader("noch übrige Sprecher")
                st.write(st.session_state.remaining_speakers)
            else:
                st.success("Alle Sprecher wurden ihrer Gruppe hinzugefügt.")

        with right_col:
            st.subheader("Füge Sprecher den normalisierten Gruppen hinzu")
            for group_name in list(st.session_state.speaker_groups.keys()):
                st.write(f"### {group_name}")
                selected = st.multiselect(
                    f"Wähle Sprecher, um sie {group_name} hinzuzufügen",
                    st.session_state.remaining_speakers,
                    key=f"select_{group_name}",
                )
                if st.button(f"Füge hin zu {group_name}", key=f"add_{group_name}"):
                    for sel in selected:
                        st.session_state.speaker_groups[group_name].append(sel)
                        st.session_state.remaining_speakers.remove(sel)
                    st.success(f"{len(selected)} Sprecher zu {group_name} hinzugefügt")

        if st.button("Normalisieren und Datei speichern"):
            normalized_text = text
            for group_name, variants in st.session_state.speaker_groups.items():
                for variant in variants:
                    pattern = r"^@" + re.escape(variant) + r"$"
                    normalized_text = re.sub(pattern, group_name, normalized_text, flags=re.MULTILINE)
            with open(FILE_OUT, "w", encoding="utf-8") as f_out:
                f_out.write(normalized_text)
            st.success(f"Datei normalisiert und gespeichert nach {FILE_OUT}")
            st.session_state.current_edit_path = FILE_OUT
            st.session_state.editor_section    = SECTION_ID
            st.rerun()

    st.divider()
    st.subheader("Datei direkt in der App bearbeiten")
    render_file_editor(SECTION_ID)
