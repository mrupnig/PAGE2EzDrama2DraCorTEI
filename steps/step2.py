import re
from pathlib import Path

import streamlit as st

from modules.paths import get_step_paths
from modules.project import Project
from steps.utils import render_file_editor, render_step_status

SECTION_ID = "sec2"


def render() -> None:
    st.markdown("---")
    st.header("2️⃣ Übersehene Speaker finden")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen.")
        return

    render_step_status("step2")

    paths = get_step_paths(project.project_dir)
    file_in  = paths["step1"]
    file_out = paths["step2"]

    if "speaker_line_selection" not in st.session_state:
        st.session_state.speaker_line_selection = {}

    if st.button("Übersehene Speaker suchen"):
        if not file_in.exists():
            st.error(f"Eingabedatei nicht gefunden: {file_in} — bitte zuerst Schritt 1 ausführen.")
            return
        lines = file_in.read_text(encoding="utf-8").splitlines(keepends=True)

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
            if not file_in.exists():
                st.error(f"Eingabedatei nicht gefunden: {file_in}")
                return
            lines = file_in.read_text(encoding="utf-8").splitlines(keepends=True)

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

            file_out.parent.mkdir(parents=True, exist_ok=True)
            file_out.write_text("\n".join(processed_lines) + "\n", encoding="utf-8")

            project.save_step("step2", file_out, {})

            st.success(f"Gespeichert: {file_out}")
            st.session_state.current_edit_path = str(file_out)
            st.session_state.editor_section    = SECTION_ID
            st.rerun()

    st.divider()
    st.subheader("Datei direkt in der App bearbeiten")
    render_file_editor(SECTION_ID)
