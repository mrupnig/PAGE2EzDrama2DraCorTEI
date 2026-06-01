import re
from collections.abc import Iterator
from pathlib import Path

import streamlit as st

from modules.paths import get_step_paths
from modules.project import Project
from steps.utils import render_step_status


def render() -> None:
    st.markdown("---")
    st.header("3️⃣ Klammer-Zeilen extrahieren")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen.")
        return

    render_step_status("step3")

    paths = get_step_paths(project.project_dir)
    file_in  = paths["step2"]
    file_out = paths["step3"]

    if "editable_bracket_contents" not in st.session_state:
        st.session_state.editable_bracket_contents = []

    if st.button("Klammer-Inhalte extrahieren"):
        if not file_in.exists():
            st.error(f"Eingabedatei nicht gefunden: {file_in} — bitte zuerst Schritt 2 ausführen.")
            return
        text = file_in.read_text(encoding="utf-8")
        bracket_contents = re.findall(r"(?s)(\(.*?\))", text)

        if bracket_contents:
            st.session_state.editable_bracket_contents = bracket_contents
            st.success(f"{len(bracket_contents)} Klammer-Inhalte erfolgreich extrahiert.")
        else:
            st.info("Keine Klammer-Inhalte gefunden.")

    if st.session_state.get("editable_bracket_contents"):
        st.write("### Gefundene Klammer-Inhalte zur Bearbeitung")
        updated_contents: list[str] = []
        for idx, content in enumerate(st.session_state.editable_bracket_contents):
            edited = st.text_area(f"Fund {idx + 1}", value=content.strip(), height=80)
            updated_contents.append(edited)

        if st.button("Änderungen übernehmen und speichern"):
            if not file_in.exists():
                st.error(f"Eingabedatei nicht gefunden: {file_in}")
                return
            text = file_in.read_text(encoding="utf-8")

            def replacement_generator() -> Iterator[str]:
                for new_content in updated_contents:
                    yield new_content

            replacer = replacement_generator()

            def replace_match(match: re.Match[str]) -> str:
                return next(replacer)

            new_text = re.sub(r"(?s)(\(.*?\))", replace_match, text, count=len(updated_contents))

            file_out.parent.mkdir(parents=True, exist_ok=True)
            file_out.write_text(new_text, encoding="utf-8")

            project.save_step("step3", file_out, {})

            st.success(f"Gespeichert: {file_out}")
