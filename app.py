import uuid
from pathlib import Path

import streamlit as st

from steps.step1 import render as step1
from steps.step2 import render as step2
from steps.step3 import render as step3
from steps.step4 import render as step4
from steps.step5 import render as step5
from steps.step6 import render as step6

if "session_dir" not in st.session_state:
    st.session_state.session_dir = Path("uploads") / str(uuid.uuid4())
    st.session_state.session_dir.mkdir(parents=True, exist_ok=True)

if "data_dir" not in st.session_state:
    st.session_state.data_dir = None

st.title("PAGE to EzDrama to DraCorTEI")
st.text("Mit dieser Anwendung können Dramen von PAGE zu DraCor-TEI konvertiert werden.")

step1()
step2()
step3()
step4()
step5()
step6()
