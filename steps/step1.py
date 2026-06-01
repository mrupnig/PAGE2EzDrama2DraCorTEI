import re
from pathlib import Path

import streamlit as st

from modules.GetSpeakers import (
    compute_similarity,
    extract_figuren,
    extract_sentences_with_dot_and_limit,
    extract_toc_entries,
)
from modules.PAGE2EzDrama import page2ezdrama
from modules.paths import get_step_paths
from modules.project import Project
from steps.utils import render_file_editor, render_step_status

SECTION_ID = "sec1"


def render() -> None:
    st.header("1️⃣ Preprocessing")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen. Bitte unter 'Projekte' ein Projekt öffnen.")
        return

    render_step_status("step1")

    paths = get_step_paths(project.project_dir)
    source_dir = paths["source"]

    xml_files = sorted(source_dir.glob("*.xml")) if source_dir.exists() else []
    if not xml_files:
        st.warning(f"Keine XML-Dateien in `{source_dir}`. Bitte PAGE-XML-Dateien dort ablegen.")
    else:
        st.info(f"{len(xml_files)} XML-Datei(en) in `{source_dir}`")

    # Metadaten aus project.json als Standardwerte
    m = project.metadata
    title    = st.text_input("Titel des Dramas",      value=m.get("title") or "")
    subtitle = st.text_input("Untertitel des Dramas",  value=m.get("subtitle") or "")
    author   = st.text_input("Autor des Dramas",       value=m.get("author") or "")
    all_metadata = f"@title {title}\n@subtitle {subtitle}\n@author {author}\n"

    if st.button("Preprocessing starten"):
        if not xml_files:
            st.error("Keine XML-Dateien gefunden.")
        else:
            with st.spinner("Extrahiere und bereite Daten vor..."):
                try:
                    data_dir = str(source_dir)
                    dramatis_personae = extract_toc_entries(data_dir)
                    speaker_list_raw, speaker_examples = extract_sentences_with_dot_and_limit(data_dir)
                    figuren = extract_figuren(dramatis_personae)
                    st.session_state.dramatis_personae   = dramatis_personae
                    st.session_state.speaker_list_raw    = speaker_list_raw
                    st.session_state.speaker_examples    = speaker_examples
                    st.session_state.figuren             = figuren
                    st.success("Preprocessing abgeschlossen.")
                except Exception as e:
                    st.error(f"Fehler beim Preprocessing: {e}")

    if "speaker_list_raw" in st.session_state:
        st.write(f"**Extrahierte Figuren:** {st.session_state.dramatis_personae}")
        st.write(f"**Bereinigte Figuren aus TOC:** {st.session_state.figuren}")
        st.write("### Interaktive Validierung der Sprecher")

        if "speaker_selection" not in st.session_state:
            st.session_state.speaker_selection = {
                speaker: False for speaker in st.session_state.speaker_list_raw
            }

        with st.form("speaker_validation_form"):
            for speaker in sorted(st.session_state.speaker_list_raw):
                match, score = compute_similarity(speaker, st.session_state.figuren)
                cleaned_speaker = re.sub(r"[^\w\s]", "", speaker).strip().lower()

                example = st.session_state.speaker_examples.get(cleaned_speaker)
                if example is None:
                    for token in cleaned_speaker.split():
                        example = st.session_state.speaker_examples.get(token)
                        if example:
                            break
                if example is None:
                    example = "(kein Beispiel verfügbar)"

                example_count = sum(
                    1 for key in st.session_state.speaker_examples
                    if cleaned_speaker in key or any(t in key for t in cleaned_speaker.split())
                )

                color = "#ffcccc" if score < 0.5 else "#fff2cc" if score < 0.75 else "#ccffcc"
                cols = st.columns([3, 1])
                with cols[0]:
                    st.markdown(f"""
                        <div style='background-color:{color};padding:10px;border-radius:5px;'>
                        <p style='margin:0'><strong>{speaker}</strong>
                        ({example_count} Matches: {match}, Score: {score:.3f})</p>
                        <p style='margin:0'><em>Beispiel:</em> {example}</p>
                        </div>
                    """, unsafe_allow_html=True)
                with cols[1]:
                    st.session_state.speaker_selection[speaker] = st.checkbox(
                        "", key=f"chk_{speaker}",
                        value=st.session_state.speaker_selection[speaker],
                    )

            submitted = st.form_submit_button("Textdatei mit gewählten Sprechern erstellen")

        if submitted:
            valid_speakers = [s for s, keep in st.session_state.speaker_selection.items() if keep]
            if valid_speakers:
                try:
                    output_path = paths["step1"]
                    result_path, file_errors = page2ezdrama(
                        data_dir=str(source_dir),
                        output_path=output_path,
                        all_metadata=all_metadata,
                        speaker_list=valid_speakers,
                    )
                    for err in file_errors:
                        st.warning(f"Übersprungene Datei: {err}")

                    project.save_step("step1", result_path, {
                        "speaker_selection": st.session_state.speaker_selection,
                        "dramatis_personae": st.session_state.get("dramatis_personae", []),
                        "figuren": st.session_state.get("figuren", []),
                    })
                    # Metadaten aus Eingabefeldern synchronisieren
                    project.save_metadata({"title": title, "subtitle": subtitle, "author": author})

                    st.success(f"Gespeichert: {result_path}")
                    st.session_state.current_edit_path = str(result_path)
                    st.session_state.editor_section    = SECTION_ID
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler bei der Vorverarbeitung: {e}")
            else:
                st.warning("Bitte mindestens einen Sprecher auswählen.")

    st.divider()
    st.subheader("Datei direkt in der App bearbeiten")
    render_file_editor(SECTION_ID)
