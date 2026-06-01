from collections import defaultdict
from pathlib import Path

import streamlit as st

from modules.paths import BASE_DIR
from modules.project import Project, slugify


def render() -> None:
    st.title("PageToDraCor")
    st.write("Konvertierung von Dramentexten: PAGE-XML → EzDrama → DraCor-TEI")

    project: Project | None = st.session_state.get("project")

    if project:
        st.success(f"Aktives Projekt: **{project.name}**")
        st.caption(f"Verzeichnis: `{project.project_dir}`")
        if st.button("Projekt schließen", type="secondary"):
            for key in ("project", "project_dir"):
                st.session_state.pop(key, None)
            st.rerun()
        st.divider()

    # ── Neues Projekt anlegen ────────────────────────────────────────────────
    with st.expander("Neues Projekt anlegen", expanded=project is None):
        name = st.text_input("Projektname", placeholder="z. B. Faust")
        if name:
            st.caption(f"Ordnername: `{slugify(name)}`")

        col1, col2 = st.columns(2)
        with col1:
            is_prose = st.checkbox("Prosa-Drama", value=True,
                                   help="Deaktivieren für Versdrama.")
        with col2:
            bracketstages = st.checkbox("Regieanweisungen in Klammern",
                                        value=True,
                                        help="bracketstages-Modus im TEI-Parser.")

        if st.button("Projekt anlegen", disabled=not name):
            try:
                new_project = Project.create(name, is_prose, bracketstages)
                st.session_state["project"] = new_project
                st.session_state["project_dir"] = new_project.project_dir
                source_path = new_project.project_dir / "source"
                st.success(
                    f"Projekt **{name}** angelegt. "
                    f"Bitte PAGE-XML-Dateien in `{source_path}` ablegen."
                )
                st.rerun()
            except ValueError as e:
                st.error(str(e))

    # ── Vorhandene Projekte ──────────────────────────────────────────────────
    st.subheader("Vorhandene Projekte")
    projects = Project.list_all()
    if not projects:
        st.info(f"Noch keine Projekte unter `{BASE_DIR / 'projects'}` vorhanden.")
        return

    for p in projects:
        is_active = project and project.slug == p.slug
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                label = f"**{p.name}**"
                if is_active:
                    label += " ✓"
                st.write(label)
                st.caption(f"`{p.slug}` · geändert: {p.modified}")
                _render_step_summary(p)
            with col2:
                if not is_active:
                    if st.button("Laden", key=f"load_{p.slug}"):
                        st.session_state["project"] = p
                        st.session_state["project_dir"] = p.project_dir
                        _restore_step_states(p)
                        st.rerun()


def _render_step_summary(project: Project) -> None:
    icons = {"pending": "⏳", "done": "✅", "stale": "⚠️", "error": "❌", "running": "🔄"}
    labels = ["Preprocessing", "Speaker", "Klammern", "Normalisierung", "Bereinigen", "TEI"]
    keys   = ["step1", "step2", "step3", "step4", "step5", "step6"]
    parts  = [f"{icons.get(project.get_step(k)['status'], '⏳')} {l}" for k, l in zip(keys, labels)]
    st.caption("  ·  ".join(parts))


def _restore_step_states(project: Project) -> None:
    """Lädt persistierte Schritt-Zustände in session_state."""
    step1_state = project.get_step("step1")["state"]
    if step1_state:
        for key in ("speaker_selection", "dramatis_personae", "figuren",
                    "speaker_list_raw", "speaker_examples"):
            if key in step1_state:
                st.session_state[key] = step1_state[key]

    step4_state = project.get_step("step4")["state"]
    if step4_state.get("speaker_groups"):
        st.session_state["speaker_groups"] = defaultdict(list, step4_state["speaker_groups"])
        st.session_state["remaining_speakers"] = step4_state.get("remaining_speakers", [])
        st.session_state["text_loaded"] = True
