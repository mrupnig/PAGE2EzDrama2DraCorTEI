import streamlit as st

from pages.home import render as home_render
from pages.metadata import render as metadata_render
from pages.settings import render as settings_render
from steps.step0 import render as step0_render
from steps.step1 import render as step1_render
from steps.step2 import render as step2_render
from steps.step3 import render as step3_render
from steps.step4 import render as step4_render
from steps.step5 import render as step5_render
from steps.step6 import render as step6_render

if "project" not in st.session_state:
    st.session_state.project = None
if "project_dir" not in st.session_state:
    st.session_state.project_dir = None

project = st.session_state.get("project")

# Step 0 nur bei Projekten mit Bild-Eingabe anzeigen
pipeline_pages = []
if project and project.settings.get("input_type") == "images":
    pipeline_pages.append(
        st.Page(step0_render, title="OCR-Pipeline", icon="0️⃣", url_path="step0")
    )
pipeline_pages += [
    st.Page(step1_render, title="Preprocessing",  icon="1️⃣", url_path="step1"),
    st.Page(step2_render, title="Speaker finden", icon="2️⃣", url_path="step2"),
    st.Page(step3_render, title="Klammern",       icon="3️⃣", url_path="step3"),
    st.Page(step4_render, title="Normalisierung", icon="4️⃣", url_path="step4"),
    st.Page(step5_render, title="Bereinigen",     icon="5️⃣", url_path="step5"),
    st.Page(step6_render, title="TEI Export",     icon="6️⃣", url_path="step6"),
]

pg = st.navigation(
    {
        "": [
            st.Page(home_render, title="Projekte", icon="🏠", default=True, url_path="home"),
        ],
        "Pipeline": pipeline_pages,
        "Projekt": [
            st.Page(metadata_render, title="Metadaten",    icon="📋", url_path="metadata"),
            st.Page(settings_render, title="Einstellungen", icon="⚙️", url_path="settings"),
        ],
    }
)

# Sidebar: Projekt-Status
if project:
    with st.sidebar:
        st.divider()
        st.caption(f"📁 **{project.name}**")

        _STATUS = {
            "pending": "⏳", "done": "✅",
            "stale":   "⚠️", "error": "❌", "running": "🔄", "skipped": "⏭️",
        }
        _LABELS = {
            "step0": "OCR-Pipeline",
            "step1": "Preprocessing",
            "step2": "Speaker finden",
            "step3": "Klammern",
            "step4": "Normalisierung",
            "step5": "Bereinigen",
            "step6": "TEI Export",
        }

        show_step0 = project.settings.get("input_type") == "images"
        for key, label in _LABELS.items():
            if key == "step0" and not show_step0:
                continue
            status = project.get_step(key)["status"]
            st.caption(f"{_STATUS.get(status, '⏳')} {label}")

pg.run()
