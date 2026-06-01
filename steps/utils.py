from pathlib import Path

import streamlit as st


def load_text(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return ""


def render_step_status(step_key: str) -> None:
    """Zeigt Status-Badge und History-Viewer für einen Schritt."""
    project = st.session_state.get("project")
    if project is None:
        return

    step = project.get_step(step_key)
    status = step["status"]
    _LABELS = {
        "pending": ("⏳", "Ausstehend"),
        "running": ("🔄", "Läuft"),
        "done":    ("✅", "Abgeschlossen"),
        "stale":   ("⚠️", "Veraltet — Vorschritt wurde neu ausgeführt"),
        "error":   ("❌", "Fehler"),
    }
    icon, label = _LABELS.get(status, ("⏳", status))
    completed = f" · {step['completed_at']}" if step.get("completed_at") else ""
    st.caption(f"{icon} {label}{completed}")

    history = project.get_history(step_key)
    if history:
        with st.expander(f"🕐 {len(history)} Version(en) im Verlauf"):
            for hf in history:
                parts = hf.stem.split("_", 1)
                ts = parts[1] if len(parts) == 2 else hf.stem
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(ts)
                with col2:
                    if st.button("↩ Wiederherstellen", key=f"rb_{hf.name}"):
                        project.rollback(step_key, hf)
                        st.success(f"Version {ts} wiederhergestellt.")
                        st.rerun()


def render_file_editor(section_id: str) -> None:
    """Inline-Datei-Editor. Wird nur angezeigt, wenn editor_section == section_id."""
    edit_path: str | None = st.session_state.get("current_edit_path")

    if st.session_state.get("editor_section") != section_id:
        st.info("Noch keine Datei zum Bearbeiten. Führe zuerst den Speicherschritt aus.")
        return

    if not edit_path or not Path(edit_path).exists():
        st.info("Noch keine Datei zum Bearbeiten. Führe zuerst den Speicherschritt aus.")
        return

    file_path = Path(edit_path)
    form_key = f"{section_id}__edit_file_form__{file_path.name}"
    ta_key   = f"{section_id}__editor_textarea__{file_path.name}"

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
            file_path.write_text(editor_value, encoding="utf-8")
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
            file_name=file_path.name,
            mime="text/plain",
        )
