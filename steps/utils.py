import os
from pathlib import Path

import streamlit as st


def load_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def render_file_editor(section_id: str) -> None:
    """Inline-Datei-Editor. Wird nur angezeigt, wenn editor_section == section_id."""
    edit_path: str | None = st.session_state.get("current_edit_path")

    if st.session_state.get("editor_section") != section_id:
        st.info("Noch keine Datei zum Bearbeiten. Führe zuerst den Speicherschritt aus.")
        return

    if not edit_path or not os.path.exists(edit_path):
        st.info("Noch keine Datei zum Bearbeiten. Führe zuerst den Speicherschritt aus.")
        return

    file_name = Path(edit_path).name
    form_key = f"{section_id}__edit_file_form__{file_name}"
    ta_key   = f"{section_id}__editor_textarea__{file_name}"

    if st.session_state.get("_editor_path") != edit_path or "editor_text" not in st.session_state:
        st.session_state.editor_text = load_text(edit_path)
        st.session_state._editor_path = edit_path

    with st.expander(f"Datei bearbeiten: {edit_path}", expanded=True):
        with st.form(form_key, clear_on_submit=False):
            editor_value = st.text_area(
                "Inhalt bearbeiten",
                value=st.session_state.editor_text,
                height=420,
                key=ta_key,
            )
            c1, c2, c3 = st.columns(3)
            with c1:
                save_clicked = st.form_submit_button("Änderungen speichern")
            with c2:
                reload_clicked = st.form_submit_button("Original neu laden")
            with c3:
                download_clicked = st.form_submit_button("Als Datei herunterladen")

    if save_clicked:
        try:
            with open(edit_path, "w", encoding="utf-8") as f:
                f.write(editor_value)
            st.session_state.editor_text = editor_value
            st.success("Gespeichert.")
        except Exception as e:
            st.error(f"Fehler beim Speichern: {e}")

    if reload_clicked:
        st.session_state.editor_text = load_text(edit_path)
        st.rerun()

    if download_clicked:
        st.download_button(
            label="Download starten",
            data=editor_value.encode("utf-8"),
            file_name=file_name,
            mime="text/plain",
        )
