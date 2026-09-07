import streamlit as st
from services.docx_service import extract_docx_text
from services.entity_extractor import extract_entities
from services.ocr_service import extract_scanned_pdf_text
from services.pdf_service import extract_pdf_text
from services.vendor_profile_builder import build_vendor_profile

st.title("Document Upload")
st.caption("Upload source documents, extract text, and prepare a consolidated vendor profile.")

files = st.file_uploader("Vendor documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)
if files:
    st.write("Uploaded files")
    for file in files:
        st.write(f"- {file.name}")

if st.button("Extract entities", type="primary", disabled=not files):
    extractions = []
    extraction_messages = []
    progress = st.progress(0)
    for index, file in enumerate(files):
        content = file.getvalue()
        suffix = file.name.lower().rsplit(".", 1)[-1]
        if suffix == "pdf":
            text = extract_pdf_text(content) or extract_scanned_pdf_text(content)
        elif suffix == "docx":
            text = extract_docx_text(content)
        else:
            text = content.decode("utf-8", errors="replace")
        if not text.strip():
            extraction_messages.append(f"{file.name}: no text could be extracted. Install OCR dependencies for scanned PDFs or verify the document.")
        else:
            extraction_messages.append(f"{file.name}: extracted {len(text):,} characters.")
        entities = extract_entities(text)
        extractions.append(entities)
        st.session_state.setdefault("source_texts", {})[file.name] = text
        progress.progress((index + 1) / len(files))
    st.session_state["vendor_profile"] = build_vendor_profile(extractions).to_dict()
    st.session_state["extraction_complete"] = True
    for message in extraction_messages:
        (st.warning if "no text" in message else st.caption)(message)
    if any("no text" in message for message in extraction_messages):
        st.error("No usable text was extracted. The profile cannot be populated until text extraction succeeds.")
    else:
        st.success("Extraction complete. Open the Validation page to review the profile.")

if st.session_state.get("extraction_complete"):
    profile = st.session_state["vendor_profile"]
    st.metric("Vendor", profile.get("vendor_name") or "Needs validation")
    st.write(f"{len(profile['directors'])} directors, {len(profile['shareholders'])} shareholders, {len(profile['ubo'])} UBOs")
