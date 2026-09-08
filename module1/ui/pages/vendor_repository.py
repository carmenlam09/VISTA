import streamlit as st
from api_client import get_vendor, search_vendors

st.title("Vendor Repository")
query = st.text_input("Search vendor name or registration number")
vendors = search_vendors(query)
if not vendors:
    st.info("No vendor profiles found.")
    st.stop()

selected_id = st.selectbox("Select vendor", vendors, format_func=lambda item: f"{item['vendor_name']} ({item.get('registration_number') or 'no registration number'})", key="vendor_select")["vendor_id"]
vendor = get_vendor(selected_id)
st.subheader(vendor["vendor_name"])
col1, col2, col3 = st.columns(3)
col1.write(f"**Registration:** {vendor.get('registration_number') or '-'}")
col2.write(f"**Country:** {vendor.get('country') or '-'}")
col3.write(f"**Created:** {vendor.get('created_date') or '-'}")
st.write(f"**Address:** {vendor.get('address') or '-'}")
for title, key in [("Directors", "directors"), ("Shareholders", "shareholders"), ("UBOs", "ubo"), ("Related parties", "related_parties")]:
    st.subheader(title)
    rows = vendor.get(key, [])
    st.dataframe(rows, use_container_width=True, hide_index=True) if rows else st.caption("None recorded")
