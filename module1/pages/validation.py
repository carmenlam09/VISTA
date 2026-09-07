import json

import streamlit as st
from services.database_service import save_vendor

st.title("Validation")
profile = st.session_state.get("vendor_profile")
if not profile:
    st.warning("Upload and extract documents first.")
    st.stop()

with st.form("vendor_profile"):
    st.subheader("Vendor details")
    vendor_name = st.text_input("Vendor name", profile.get("vendor_name", ""))
    registration_number = st.text_input("Registration number", profile.get("registration_number", ""))
    country = st.text_input("Country", profile.get("country", ""))
    address = st.text_area("Address", profile.get("address", ""))

    st.subheader("Directors")
    directors = st.data_editor(profile.get("directors", []), num_rows="dynamic", use_container_width=True, key="directors_editor")
    st.subheader("Shareholders")
    shareholders = st.data_editor(profile.get("shareholders", []), num_rows="dynamic", use_container_width=True, key="shareholders_editor")
    st.subheader("Ultimate beneficial owners")
    ubos = st.data_editor(profile.get("ubo", []), num_rows="dynamic", use_container_width=True, key="ubo_editor")
    st.subheader("Related parties")
    related_parties = st.data_editor(profile.get("related_parties", []), num_rows="dynamic", use_container_width=True, key="related_editor")

    submitted = st.form_submit_button("Save vendor profile", type="primary")

if submitted:
    updated = {"vendor_name": vendor_name.strip(), "registration_number": registration_number.strip(), "country": country.strip(), "address": address.strip(), "directors": directors.to_dict("records"), "shareholders": shareholders.to_dict("records"), "ubo": ubos.to_dict("records"), "related_parties": related_parties.to_dict("records")}
    if not updated["vendor_name"]:
        st.error("Vendor name is required.")
    else:
        vendor_id = save_vendor(updated)
        st.session_state["vendor_profile"] = updated
        st.success(f"Vendor profile saved with ID {vendor_id}.")

st.download_button(
    "Download profile JSON",
    data=json.dumps(profile, indent=2, ensure_ascii=True),
    file_name="vendor_profile.json",
    mime="application/json",
)
