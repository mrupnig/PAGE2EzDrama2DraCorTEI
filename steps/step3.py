import os
import re
from collections.abc import Iterator

import streamlit as st

FILE_IN  = "output/2_drama_speaker_fixed.txt"
FILE_OUT = "output/3_drama_brackets_fixed.txt"


def render() -> None:
    st.markdown("---")
    st.header("3️⃣ Klammer-Zeilen extrahieren")

    if "editable_bracket_contents" not in st.session_state:
        st.session_state.editable_bracket_contents = []

    if st.button("Klammer-Inhalte extrahieren"):
        if not os.path.exists(FILE_IN):
            st.error(f"Eingabedatei nicht gefunden: {FILE_IN} — bitte zuerst Schritt 2 ausführen.")
            return
        with open(FILE_IN, "r", encoding="utf-8") as f:
            text = f.read()

        bracket_contents = re.findall(r"(?s)(\(.*?\))", text)

        if bracket_contents:
            st.session_state.editable_bracket_contents = bracket_contents
            st.success(f"{len(bracket_contents)} Klammer-Inhalte erfolgreich extrahiert. Jetzt bearbeitbar.")
        else:
            st.info("Keine Klammer-Inhalte gefunden.")

    if st.session_state.get("editable_bracket_contents"):
        st.write("### Gefundene Klammer-Inhalte zur Bearbeitung")
        updated_contents: list[str] = []
        for idx, content in enumerate(st.session_state.editable_bracket_contents):
            edited = st.text_area(f"Fund {idx + 1}", value=content.strip(), height=80)
            updated_contents.append(edited)

        if st.button("Änderungen übernehmen und speichern"):
            if not os.path.exists(FILE_IN):
                st.error(f"Eingabedatei nicht gefunden: {FILE_IN}")
                return
            with open(FILE_IN, "r", encoding="utf-8") as f:
                text = f.read()

            def replacement_generator() -> Iterator[str]:
                for new_content in updated_contents:
                    yield new_content

            replacer = replacement_generator()

            def replace_match(match: re.Match[str]) -> str:
                return next(replacer)

            new_text = re.sub(r"(?s)(\(.*?\))", replace_match, text, count=len(updated_contents))

            with open(FILE_OUT, "w", encoding="utf-8") as f:
                f.write(new_text)

            st.success(f"Alle Änderungen wurden übernommen und gespeichert unter: {FILE_OUT}")
