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
from modules.paths import BASE_DIR, get_step_paths
from steps.utils import render_file_editor

SECTION_ID = "sec1"


def _select_project_dir() -> None:
    """Temporäre Projektwahl per Pfadeingabe – wird in Phase 1 durch Projektmanager ersetzt."""
    st.write("### Projektverzeichnis")
    default = str(BASE_DIR / "projects")
    raw = st.text_input("Pfad zum Projektverzeichnis", value=str(st.session_state.project_dir or default))
    if st.button("Verzeichnis setzen"):
        p = Path(raw)
        if not p.exists():
            st.error(f"Verzeichnis nicht gefunden: {p}")
        else:
            st.session_state.project_dir = p
            st.success(f"Projektverzeichnis gesetzt: {p}")
            st.rerun()


def render() -> None:
    st.header("1️⃣ Preprocessing", anchor="preprocessing")

    project_dir: Path | None = st.session_state.get("project_dir")
    if project_dir is None:
        _select_project_dir()
        return

    paths = get_step_paths(project_dir)
    source_dir = paths["source"]

    _select_project_dir()
    st.divider()

    xml_files = list(source_dir.glob("*.xml")) if source_dir.exists() else []
    if not xml_files:
        st.warning(f"Keine XML-Dateien in `{source_dir}` gefunden. Bitte PAGE-XML-Dateien dort ablegen.")
    else:
        st.info(f"{len(xml_files)} XML-Datei(en) in `{source_dir}`")

    title    = st.text_input("Titel des Dramas",      value="Titel ...")
    subtitle = st.text_input("Untertitel des Dramas",  value="Untertitel ...")
    author   = st.text_input("Autor des Dramas",       value="Autor")
    all_metadata = f"@title {title}\n@subtitle {subtitle}\n@author {author}\n"

    if st.button("Preprocessing starten"):
        if not xml_files:
            st.error("Keine XML-Dateien gefunden. Bitte zuerst Dateien in den source/-Ordner legen.")
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
                    st.success(f"Gespeichert: {result_path}")
                    st.session_state.current_edit_path = str(result_path)
                    st.session_state.editor_section    = SECTION_ID
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler bei der Vorverarbeitung: {e}")
            else:
                st.warning("Bitte mindestens einen Sprecher auswählen, bevor die Datei erstellt wird.")

    st.divider()
    st.subheader("Datei direkt in der App bearbeiten")
    render_file_editor(SECTION_ID)
