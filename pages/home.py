import shutil
from collections import defaultdict
from pathlib import Path

import streamlit as st

from modules.paths import BASE_DIR
from modules.project import Project, slugify

_STEP_ICONS = {
    "pending": "⏳", "done": "✅", "stale": "⚠️",
    "error": "❌", "running": "🔄", "skipped": "⏭️",
}


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

        input_type = st.radio(
            "Eingabemodus",
            options=["page_xml", "images"],
            format_func=lambda x: (
                "PAGE-XML (bestehend)" if x == "page_xml"
                else "Bilder / Scans (OCR in der App)"
            ),
            help=(
                "PAGE-XML: Dateien aus OCR4all oder anderer OCR-Software direkt verwenden. "
                "Bilder: Scans werden über die eingebaute OCR-Pipeline (Kraken + Calamari) verarbeitet."
            ),
            horizontal=True,
        )

        if st.button("Projekt anlegen", disabled=not name):
            try:
                new_project = Project.create(name, is_prose, bracketstages, input_type=input_type)
                st.session_state["project"] = new_project
                st.session_state["project_dir"] = new_project.project_dir

                if input_type == "images":
                    source_path = new_project.project_dir / "source" / "images"
                    hint = f"Bitte Bilddateien (jpg/png/tif) in `{source_path}` ablegen, dann OCR-Pipeline starten."
                else:
                    source_path = new_project.project_dir / "source"
                    hint = f"Bitte PAGE-XML-Dateien in `{source_path}` ablegen."

                st.success(f"Projekt **{name}** angelegt. {hint}")
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
        confirm_key = f"confirm_delete_{p.slug}"
        with st.container(border=True):
            col1, col2 = st.columns([5, 1])
            with col1:
                label = f"**{p.name}**"
                if is_active:
                    label += " ✓"
                st.write(label)
                input_badge = (
                    "🖼️ Bilder/OCR" if p.settings.get("input_type") == "images"
                    else "📄 PAGE-XML"
                )
                llm_badge = (
                    "🤖 KI-unterstützt" if p.settings.get("llm_mode") == "assisted"
                    else "✋ Manuell"
                )
                st.caption(f"`{p.slug}` · {input_badge} · {llm_badge} · geändert: {p.modified}")
                _render_step_summary(p)
            with col2:
                if not is_active:
                    if st.button("Laden", key=f"load_{p.slug}"):
                        st.session_state["project"] = p
                        st.session_state["project_dir"] = p.project_dir
                        _restore_step_states(p)
                        st.rerun()
                if st.button("Löschen", key=f"delete_{p.slug}", type="secondary"):
                    st.session_state[confirm_key] = True
                    st.rerun()

            if st.session_state.get(confirm_key):
                st.warning(
                    f"Projekt **{p.name}** und alle Dateien unwiderruflich löschen?"
                )
                c1, c2, _ = st.columns([1, 1, 3])
                with c1:
                    if st.button("Ja, löschen", key=f"del_yes_{p.slug}", type="primary"):
                        if is_active:
                            for k in ("project", "project_dir"):
                                st.session_state.pop(k, None)
                        shutil.rmtree(p.project_dir)
                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                with c2:
                    if st.button("Abbrechen", key=f"del_no_{p.slug}"):
                        st.session_state.pop(confirm_key, None)
                        st.rerun()


def _render_step_summary(project: Project) -> None:
    input_type = project.settings.get("input_type", "page_xml")

    all_steps = [
        ("step0", "OCR"),
        ("step1", "Preprocessing"),
        ("step2", "Speaker"),
        ("step3", "Klammern"),
        ("step4", "Normalisierung"),
        ("step5", "Bereinigen"),
        ("step6", "TEI"),
    ]

    parts = []
    for key, label in all_steps:
        if key == "step0" and input_type != "images":
            continue
        status = project.get_step(key)["status"]
        parts.append(f"{_STEP_ICONS.get(status, '⏳')} {label}")

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
