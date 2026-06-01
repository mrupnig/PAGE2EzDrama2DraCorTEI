from pathlib import Path

import streamlit as st

from modules.DraCorParser import Parser
from modules.paths import get_step_paths


def render() -> None:
    st.markdown("---")
    st.header("6️⃣ EzDrama zu DraCor-TEI konvertieren")

    project_dir: Path | None = st.session_state.get("project_dir")
    if project_dir is None:
        st.warning("Kein Projekt geladen.")
        return

    paths = get_step_paths(project_dir)
    file_in  = paths["step5"]
    file_out = paths["step6"]

    bracketstages = st.checkbox("Klammern als Bühnenanweisungen behandeln (bracketstages)", value=True)
    is_prose      = st.checkbox("Prosa-Modus aktivieren (is_prose)", value=True)
    dracor_id     = st.text_input("Dracor ID", value="ger000000")
    dracor_lang   = st.text_input("Sprache des Dramas (dracor_lang)", value="de")

    if st.button("EzDrama to DraCor-TEI"):
        if not file_in.exists():
            st.error(f"Eingabedatei nicht gefunden: {file_in} — bitte zuerst Schritt 5 ausführen.")
            return
        with st.spinner("Konvertiere EzDrama zu DraCor-TEI..."):
            try:
                file_out.parent.mkdir(parents=True, exist_ok=True)
                parser = Parser(
                    bracketstages=bracketstages,
                    is_prose=is_prose,
                    dracor_id=dracor_id,
                    dracor_lang=dracor_lang,
                )
                parser.process_file(str(file_in), output_path=str(file_out))
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
