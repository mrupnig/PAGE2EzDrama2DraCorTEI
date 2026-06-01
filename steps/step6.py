from pathlib import Path

import streamlit as st

from modules.DraCorParser import Parser
from modules.paths import get_step_paths
from modules.project import Project
from steps.utils import render_step_status


def render() -> None:
    st.markdown("---")
    st.header("6️⃣ EzDrama zu DraCor-TEI konvertieren")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen.")
        return

    render_step_status("step6")

    paths = get_step_paths(project.project_dir)
    file_in  = paths["step5"]
    file_out = paths["step6"]

    # Einstellungen aus project.json (gesetzt beim Anlegen / auf der Metadaten-Seite)
    s = project.settings
    m = project.metadata

    st.info(
        f"Parser-Einstellungen aus dem Projekt: "
        f"Prosa={'ja' if s.get('is_prose') else 'nein'}, "
        f"Bracketstages={'ja' if s.get('bracketstages') else 'nein'} · "
        f"Änderbar auf der Metadaten-Seite."
    )

    dracor_id   = st.text_input("DraCor-ID",    value=m.get("dracor_id") or "ger000000")
    dracor_lang = st.text_input("Sprache",       value=m.get("language") or "de")

    if st.button("EzDrama zu DraCor-TEI konvertieren"):
        if not file_in.exists():
            st.error(f"Eingabedatei nicht gefunden: {file_in} — bitte zuerst Schritt 5 ausführen.")
            return
        with st.spinner("Konvertiere EzDrama zu DraCor-TEI..."):
            try:
                file_out.parent.mkdir(parents=True, exist_ok=True)
                parser = Parser(
                    bracketstages=s.get("bracketstages", True),
                    is_prose=s.get("is_prose", True),
                    dracor_id=dracor_id,
                    dracor_lang=dracor_lang,
                )
                parser.process_file(str(file_in), output_path=str(file_out))

                project.save_step("step6", file_out, {})
                # dracor_id und Sprache aus UI-Feldern zurückschreiben
                project.save_metadata({"dracor_id": dracor_id, "language": dracor_lang})

                st.success(f"Konvertierung abgeschlossen: {file_out}")

                if file_out.exists():
                    st.download_button(
                        label="XML herunterladen",
                        data=file_out.read_bytes(),
                        file_name=file_out.name,
                        mime="application/xml",
                        key="dl_xml",
                    )
                else:
                    st.error("Ausgabedatei nicht gefunden.")
            except Exception as e:
                st.error(f"Fehler bei der Konvertierung: {e}")
