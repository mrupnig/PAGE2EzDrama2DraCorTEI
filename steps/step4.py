import re
from collections import defaultdict
from pathlib import Path

import streamlit as st

from modules.paths import get_step_paths
from steps.utils import render_file_editor

SECTION_ID = "sec4"


def render() -> None:
    st.markdown("---")
    st.header("4️⃣ Interaktive Speaker-Normalisierung")

    project_dir: Path | None = st.session_state.get("project_dir")
    if project_dir is None:
        st.warning("Kein Projekt geladen.")
        return

    paths = get_step_paths(project_dir)
    file_in  = paths["step3"]
    file_out = paths["step4"]

    if st.button("Textdatei laden"):
        if not file_in.exists():
            st.error(f"Eingabedatei nicht gefunden: {file_in} — bitte zuerst Schritt 3 ausführen.")
            return
        text = file_in.read_text(encoding="utf-8")
        st.session_state.text_loaded  = True
        st.session_state.text_content = text
        st.success("Datei erfolgreich geladen.")

    if st.session_state.get("text_loaded", False):
        text = st.session_state.text_content
        speakers_raw    = re.findall(r"^@(.*?)$", text, re.MULTILINE)
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
            file_out.parent.mkdir(parents=True, exist_ok=True)
            file_out.write_text(normalized_text, encoding="utf-8")
            st.success(f"Gespeichert: {file_out}")
            st.session_state.current_edit_path = str(file_out)
            st.session_state.editor_section    = SECTION_ID
            st.rerun()

    st.divider()
    st.subheader("Datei direkt in der App bearbeiten")
    render_file_editor(SECTION_ID)
