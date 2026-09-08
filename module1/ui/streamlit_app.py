import streamlit as st

st.set_page_config(page_title="VISTA | Vendor Intelligence", page_icon="V", layout="wide")

st.title("VISTA")
st.subheader("Vendor Intelligence Screening & Trust Assessment")
st.write("Digital intake and entity extraction for vendor due diligence.")

st.info("Use the pages in the sidebar to upload documents, validate extracted entities, and search the vendor repository.")
col1, col2, col3 = st.columns(3)
col1.metric("Workflow", "3 steps")
col2.metric("Supported files", "PDF, DOCX, TXT")
col3.metric("AI mode", "Gemini + mock fallback")

st.markdown("### Module 1 workflow")
st.markdown("1. **Document Upload** - extract text and identify vendor entities.\n2. **Validation** - review, correct, and save the consolidated profile.\n3. **Vendor Repository** - search saved vendor profiles and related parties.")
