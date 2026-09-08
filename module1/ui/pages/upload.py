import streamlit as st
from api_client import extract

st.title("Document Upload")
st.caption("Upload source documents, extract text, and prepare a consolidated vendor profile.")

files = st.file_uploader("Vendor documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)
if files:
    st.write("Uploaded files")
    for file in files:
        st.write(f"- {file.name}")

if st.button("Extract entities", type="primary", disabled=not files):
    with st.spinner("Extracting..."):
        result = extract([(file.name, file.getvalue()) for file in files])
    st.session_state["vendor_profile"] = result["profile"]
    st.session_state["extraction_complete"] = True
    for message in result["messages"]:
        (st.warning if message["is_warning"] else st.caption)(f"{message['file_name']}: {message['message']}")
    if result["has_warnings"]:
        st.error("No usable text was extracted for at least one file. Review before saving.")
    else:
        st.success("Extraction complete. Open the Validation page to review the profile.")

if st.session_state.get("extraction_complete"):
    profile = st.session_state["vendor_profile"]
    st.metric("Vendor", profile.get("vendor_name") or "Needs validation")
    st.write(f"{len(profile['directors'])} directors, {len(profile['shareholders'])} shareholders, {len(profile['ubo'])} UBOs")
