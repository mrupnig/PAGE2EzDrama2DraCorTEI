import streamlit as st

from pages.home import render as home_render
from pages.metadata import render as metadata_render
from pages.settings import render as settings_render
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

pg = st.navigation(
    {
        "": [
            st.Page(home_render, title="Projekte", icon="🏠", default=True, url_path="home"),
        ],
        "Pipeline": [
            st.Page(step1_render, title="1 · Preprocessing",     icon="1️⃣", url_path="step1"),
            st.Page(step2_render, title="2 · Speaker finden",     icon="2️⃣", url_path="step2"),
            st.Page(step3_render, title="3 · Klammern",           icon="3️⃣", url_path="step3"),
            st.Page(step4_render, title="4 · Normalisierung",     icon="4️⃣", url_path="step4"),
            st.Page(step5_render, title="5 · Bereinigen",         icon="5️⃣", url_path="step5"),
            st.Page(step6_render, title="6 · TEI Export",         icon="6️⃣", url_path="step6"),
        ],
        "Projekt": [
            st.Page(metadata_render, title="Metadaten",    icon="📋", url_path="metadata"),
            st.Page(settings_render, title="Einstellungen", icon="⚙️", url_path="settings"),
        ],
    }
)

# Sidebar: project status badges
project = st.session_state.get("project")
if project:
    with st.sidebar:
        st.divider()
        st.caption(f"📁 **{project.name}**")
        _STATUS = {
            "pending": "⏳", "done": "✅",
            "stale":   "⚠️", "error": "❌", "running": "🔄",
        }
        _LABELS = {
            "step1": "Preprocessing",
            "step2": "Speaker finden",
            "step3": "Klammern",
            "step4": "Normalisierung",
            "step5": "Bereinigen",
            "step6": "TEI Export",
        }
        for key, label in _LABELS.items():
            status = project.get_step(key)["status"]
            st.caption(f"{_STATUS.get(status, '⏳')} {label}")

pg.run()
