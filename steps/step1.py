import io
import re
import zipfile
from pathlib import Path

import streamlit as st

from modules.GetSpeakers import (
    compute_similarity,
    extract_figuren,
    extract_sentences_with_dot_and_limit,
    extract_toc_entries,
)
from modules.PAGE2EzDrama import page2ezdrama
from steps.utils import render_file_editor

SECTION_ID = "sec1"


def render() -> None:
    st.header("1️⃣ Preprocessing", anchor="preprocessing")
    st.write("### Datenordner auswählen")

    session_dir: Path = st.session_state.session_dir
    mode = st.radio("Upload-Modus", ["ZIP-Ordner", "Einzelne XMLs"])

    if mode == "ZIP-Ordner":
        z = st.file_uploader("ZIP mit deinem Ordner wählen", type=["zip"])
        if z and st.button("Ordner importieren"):
            with zipfile.ZipFile(io.BytesIO(z.read())) as zf:
                for name in zf.namelist():
                    if name.lower().endswith(".xml") and not name.endswith("/"):
                        target = session_dir / Path(name).name  # flach ablegen
                        with zf.open(name) as src, open(target, "wb") as dst:
                            dst.write(src.read())
            xmls = list(session_dir.glob("*.xml"))
            if xmls:
                st.session_state.data_dir = str(session_dir)
                st.success(f"{len(xmls)} XML-Datei(en) importiert.")
            else:
                st.error("Keine XML-Dateien im ZIP gefunden.")
    else:
        files = st.file_uploader("XML-Dateien wählen", type=["xml"], accept_multiple_files=True)
        if files and st.button("Dateien importieren"):
            for uf in files:
                (session_dir / uf.name).write_bytes(uf.read())
            st.session_state.data_dir = str(session_dir)
            st.success(f"{len(list(session_dir.glob('*.xml')))} XML-Datei(en) importiert.")

    if st.session_state.data_dir:
        st.info(f"Datenpfad: {st.session_state.data_dir}")
    else:
        st.warning("Noch kein Datenpfad gesetzt. Bitte Dateien importieren.")

    title    = st.text_input("Titel des Dramas",     value="Titel ...")
    subtitle = st.text_input("Untertitel des Dramas", value="Untertitel ...")
    author   = st.text_input("Autor des Dramas",      value="Autor")
    all_metadata = f"@title {title}\n@subtitle {subtitle}\n@author {author}\n"

    if st.button("Preprocessing starten"):
        if not st.session_state.data_dir:
            st.error("Kein Datenpfad gesetzt. Bitte zuerst XML-Dateien importieren.")
        else:
            with st.spinner("Extrahiere und bereite Daten vor..."):
                try:
                    data_dir = st.session_state.data_dir
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
                    output_path, file_errors = page2ezdrama(
                        data_dir=st.session_state.data_dir,
                        output_dir="output",
                        output_filename="1_drama_preprocessed.txt",
                        all_metadata=all_metadata,
                        speaker_list=valid_speakers,
                    )
                    for err in file_errors:
                        st.warning(f"Übersprungene Datei: {err}")
                    st.success(f"Gesamtausgabe gespeichert unter: {output_path}")
                    st.session_state.current_edit_path = output_path
                    st.session_state.editor_section    = SECTION_ID
                    st.rerun()
                except Exception as e:
                    st.error(f"Fehler bei der Vorverarbeitung: {e}")
            else:
                st.warning("Bitte mindestens einen Sprecher auswählen, bevor die Datei erstellt wird.")

    st.divider()
    st.subheader("Datei direkt in der App bearbeiten")
    render_file_editor(SECTION_ID)
