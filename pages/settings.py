import streamlit as st

from modules.llm import (
    RECOMMENDED_MODELS,
    cache_stats,
    clear_cache,
    llm_available,
)
from modules.ocr import (
    get_kraken_version,
    kraken_available,
)
from modules.paths import BASE_DIR
from modules.project import Project


def render() -> None:
    st.header("⚙️ Einstellungen")

    project: Project | None = st.session_state.get("project")

    # ── 1. OCR-Tools ─────────────────────────────────────────────────────────
    st.subheader("OCR-Tools")

    if kraken_available():
        st.success(f"Kraken installiert — {get_kraken_version() or 'Version unbekannt'}")
    else:
        st.error("Kraken nicht gefunden")
        st.code("uv add kraken", language="bash")

    model_dir = BASE_DIR / "models"
    st.caption(
        f"Eigene Segmentierungsmodelle (`.mlmodel`) in `{model_dir}` ablegen. "
        "Texterkennung (OCR) erfolgt extern mit einem beliebigen Tool (Calamari, Kraken OCR, …) "
        "und wird als PAGE-XML mit TextEquiv-Elementen zurück nach `source/page/` gelegt."
    )

    if model_dir.exists():
        mlmodels = list(model_dir.glob("*.mlmodel"))
        st.caption(f"Gefundene Segmentierungsmodelle: {len(mlmodels)}")
    else:
        st.caption(f"Modellverzeichnis `{model_dir}` existiert noch nicht.")

    st.markdown(
        "**Vortrainierte Kraken-Segmentierungsmodelle:**\n"
        "`kraken list` / `kraken get <doi>` oder zenodo.org/communities/ocr-models"
    )

    st.divider()

    # ── 2. LLM / KI ──────────────────────────────────────────────────────────
    st.subheader("KI-Unterstützung (OpenRouter)")

    col_key, col_status = st.columns([3, 1])
    with col_key:
        st.markdown("**API-Key** (`OPENROUTER_API_KEY` in `.streamlit/secrets.toml`)")
    with col_status:
        if llm_available():
            st.success("Vorhanden")
        else:
            st.error("Nicht gefunden")

    if not llm_available():
        st.markdown(
            "API-Key in `.streamlit/secrets.toml` eintragen:\n"
            "```toml\nOPENROUTER_API_KEY = \"sk-or-...\"\n```"
        )

    st.markdown("**Empfohlene Modelle** (kostenlos / günstig):")
    for m in RECOMMENDED_MODELS:
        st.caption(f"• `{m}`")

    # Projektspezifische LLM-Einstellungen
    if project is None:
        st.info("Kein Projekt geladen — projektspezifische KI-Einstellungen werden angezeigt sobald ein Projekt geöffnet ist.")
    else:
        st.markdown(f"**Projekteinstellungen — {project.name}**")

        llm_settings = project.settings.get("llm", {})

        llm_mode = st.radio(
            "Modus",
            options=["manual", "assisted"],
            format_func=lambda x: "✋ Manuell" if x == "manual" else "🤖 KI-unterstützt",
            index=0 if project.settings.get("llm_mode", "manual") == "manual" else 1,
            horizontal=True,
            help="Im KI-unterstützten Modus werden LLM-Vorschläge in jedem Schritt angezeigt.",
        )

        if llm_mode == "assisted":
            st.markdown("Modell pro Schritt:")
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                model_step1 = st.selectbox(
                    "Schritt 1 — Figurenerkennung",
                    RECOMMENDED_MODELS,
                    index=_model_index(llm_settings.get("model_step1"), RECOMMENDED_MODELS),
                    key="llm_model_step1",
                )
                model_step3 = st.selectbox(
                    "Schritt 3 — Regieanweisungen",
                    RECOMMENDED_MODELS,
                    index=_model_index(llm_settings.get("model_step3"), RECOMMENDED_MODELS),
                    key="llm_model_step3",
                )
            with col_s2:
                model_step2 = st.selectbox(
                    "Schritt 2 — Übersehene Sprecher",
                    RECOMMENDED_MODELS,
                    index=_model_index(llm_settings.get("model_step2"), RECOMMENDED_MODELS),
                    key="llm_model_step2",
                )
                model_step4 = st.selectbox(
                    "Schritt 4 — Normalisierung",
                    RECOMMENDED_MODELS,
                    index=_model_index(llm_settings.get("model_step4"), RECOMMENDED_MODELS),
                    key="llm_model_step4",
                )
        else:
            model_step1 = llm_settings.get("model_step1", RECOMMENDED_MODELS[0])
            model_step2 = llm_settings.get("model_step2", RECOMMENDED_MODELS[0])
            model_step3 = llm_settings.get("model_step3", RECOMMENDED_MODELS[2])
            model_step4 = llm_settings.get("model_step4", RECOMMENDED_MODELS[0])

        if st.button("KI-Einstellungen speichern"):
            project.save_settings({
                "llm_mode": llm_mode,
                "llm": {
                    "model_step1": model_step1,
                    "model_step2": model_step2,
                    "model_step3": model_step3,
                    "model_step4": model_step4,
                },
            })
            st.success("Einstellungen gespeichert.")
            st.rerun()

    st.divider()

    # ── 3. Cache ──────────────────────────────────────────────────────────────
    st.subheader("LLM-Antwort-Cache")
    stats = cache_stats()
    st.caption(
        f"{stats['count']} gecachte Antwort(en) — {stats['size_kb']} KB "
        f"in `~/pagetodracor/llm_cache/`"
    )
    if stats["count"] > 0:
        if st.button("Cache leeren", type="secondary"):
            deleted = clear_cache()
            st.success(f"{deleted} Einträge gelöscht.")
            st.rerun()


def _model_index(model: str | None, options: list[str]) -> int:
    if model and model in options:
        return options.index(model)
    return 0
