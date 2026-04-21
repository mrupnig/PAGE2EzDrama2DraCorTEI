import os

import streamlit as st


from modules.DraCorParser import Parser

FILE_IN = "output/5_drama_text_cleaned.txt"


def render() -> None:
    st.markdown("---")
    st.header("6️⃣ EzDrama zu DraCor-TEI konvertieren")

    bracketstages = st.checkbox("Klammern als Bühnenanweisungen behandeln (bracketstages)", value=True)
    is_prose      = st.checkbox("Prosa-Modus aktivieren (is_prose)", value=True)
    dracor_id     = st.text_input("Dracor ID", value="ger000000")
    dracor_lang   = st.text_input("Sprache des Dramas (dracor_lang)", value="de")

    if st.button("EzDrama to DraCor-TEI"):
        if not os.path.exists(FILE_IN):
            st.error(f"Eingabedatei nicht gefunden: {FILE_IN} — bitte zuerst Schritt 5 ausführen.")
            return
        with st.spinner("Konvertiere EzDrama zu DraCor-TEI..."):
            try:
                parser = Parser(
                    bracketstages=bracketstages,
                    is_prose=is_prose,
                    dracor_id=dracor_id,
                    dracor_lang=dracor_lang,
                )
                parser.process_file(FILE_IN)
                st.success(f"Konvertierung abgeschlossen: {parser.outputname}")

                if os.path.exists(parser.outputname):
                    with open(parser.outputname, "rb") as f:
                        xml_bytes = f.read()
                    st.download_button(
                        label="XML herunterladen",
                        data=xml_bytes,
                        file_name=os.path.basename(parser.outputname),
                        mime="application/xml",
                        key="dl_xml",
                    )
                else:
                    st.error("Ausgabedatei nicht gefunden.")
            except Exception as e:
                st.error(f"Fehler bei der Konvertierung: {e}")
