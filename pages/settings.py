import streamlit as st

from modules.llm import (
    RECOMMENDED_MODELS,
    cache_stats,
    clear_cache,
    llm_available,
)
from modules.ocr import (
    calamari_available,
    get_calamari_version,
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

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Kraken** (Layoutsegmentierung)")
        if kraken_available():
            st.success(f"Installiert — {get_kraken_version() or 'Version unbekannt'}")
        else:
            st.error("Nicht gefunden")
            st.code("pip install kraken", language="bash")

    with col2:
        st.markdown("**Calamari** (Texterkennung)")
        if calamari_available():
            st.success(f"Installiert — {get_calamari_version() or 'Version unbekannt'}")
        else:
            st.error("Nicht gefunden")
            st.code("pip install calamari-ocr", language="bash")

    st.caption(
        f"Eigene Modelle (`.mlmodel` für Kraken, Checkpoint-Ordner für Calamari) "
        f"in `{BASE_DIR / 'models'}` ablegen."
    )

    model_dir = BASE_DIR / "models"
    if model_dir.exists():
        mlmodels   = list(model_dir.glob("*.mlmodel"))
        checkpoints = [
            d for d in model_dir.iterdir()
            if d.is_dir() and any(d.glob("*.ckpt.json"))
        ]
        st.caption(
            f"Gefundene Modelle: {len(mlmodels)} Kraken-Segmentierungsmodell(e), "
            f"{len(checkpoints)} Calamari-Checkpoint(s)"
        )
    else:
        st.caption(f"Modellverzeichnis `{model_dir}` existiert noch nicht.")

    st.markdown(
        "**Vortrainierte Modelle:**\n"
        "- Kraken: `kraken list` / `kraken get <doi>` oder [zenodo.org/communities/ocr-models](https://zenodo.org/communities/ocr-models)\n"
        "- Calamari: [github.com/Calamari-OCR/calamari_models_experimental](https://github.com/Calamari-OCR/calamari_models_experimental)"
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
