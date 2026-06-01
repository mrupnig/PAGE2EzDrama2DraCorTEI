import streamlit as st

from modules.project import Project


def render() -> None:
    st.header("📋 Metadaten")

    project: Project | None = st.session_state.get("project")
    if project is None:
        st.warning("Kein Projekt geladen. Bitte unter 'Projekte' ein Projekt öffnen.")
        return

    st.caption(f"Projekt: **{project.name}**")
    m = project.metadata
    s = project.settings

    st.subheader("Textangaben")
    title        = st.text_input("Titel",       value=m.get("title", ""))
    subtitle     = st.text_input("Untertitel",  value=m.get("subtitle", ""))
    author       = st.text_input("Autor",       value=m.get("author", ""))
    language     = st.text_input("Sprache (ISO 639-1)", value=m.get("language", "de"))

    st.subheader("DraCor")
    dracor_id    = st.text_input("DraCor-ID",   value=m.get("dracor_id", ""))
    wikidata_id  = st.text_input("Wikidata-ID", value=m.get("wikidata_id", ""))

    st.subheader("Quelle")
    source_url   = st.text_input("Quell-URL",   value=m.get("source_url", ""))
    source_inst  = st.text_input("Institution", value=m.get("source_institution", ""))

    st.subheader("Datierungen")
    col1, col2, col3 = st.columns(3)
    with col1:
        year_written  = st.text_input("Entstehung",    value=m.get("year_written", ""))
    with col2:
        year_print    = st.text_input("Erstdruck",     value=m.get("year_print", ""))
    with col3:
        year_premiere = st.text_input("Uraufführung",  value=m.get("year_premiere", ""))

    st.subheader("Parser-Einstellungen")
    is_prose      = st.checkbox("Prosa-Drama",                    value=s.get("is_prose", True))
    bracketstages = st.checkbox("Regieanweisungen in Klammern",   value=s.get("bracketstages", True))

    if st.button("Speichern", type="primary"):
        project.save_metadata({
            "title": title, "subtitle": subtitle, "author": author,
            "language": language, "dracor_id": dracor_id,
            "source_url": source_url, "source_institution": source_inst,
            "wikidata_id": wikidata_id, "year_written": year_written,
            "year_premiere": year_premiere, "year_print": year_print,
        })
        project.save_settings({"is_prose": is_prose, "bracketstages": bracketstages})
        st.success("Metadaten gespeichert.")
