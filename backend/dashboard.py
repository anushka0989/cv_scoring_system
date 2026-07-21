import os
import zipfile
import tempfile

import pandas as pd
import streamlit as st

from cv_parser import parse_cv
from save_candidate import save_candidate
from get_candidates import get_candidates
from delete_candidate import delete_candidate
import parser
parser.set_tesseract_path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")

st.set_page_config(page_title="CV Dashboard", layout="wide")

st.title("📄 CV Dashboard")
st.caption(
    "Parses CVs in the fixed INFRACON / MoRTH 'VIEW CONSULTANT DETAILS' export "
    "format only. CVs in a different format will come back mostly empty — see "
    "the warnings shown after parsing."
)

# ==========================
# BULK CV IMPORT
# ==========================

st.header("📂 Bulk CV Import")

uploaded_zip = st.file_uploader("Upload ZIP containing CVs", type=["zip"], key="zip_upload")

if uploaded_zip and st.button("🚀 Import All CVs"):
    saved = skipped = errors = 0
    progress_bar = st.progress(0)
    status = st.empty()
    error_log = []

    with tempfile.TemporaryDirectory() as temp_dir:
        zip_path = os.path.join(temp_dir, uploaded_zip.name)
        with open(zip_path, "wb") as f:
            f.write(uploaded_zip.getbuffer())

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(temp_dir)

        cv_files = [
            os.path.join(root, f)
            for root, _, files in os.walk(temp_dir)
            for f in files
            if f.lower().endswith((".pdf", ".docx"))
        ]

        total = len(cv_files)
        if total == 0:
            st.error("No PDF or DOCX files found in the ZIP.")
        else:
            os.makedirs("uploads/cvs", exist_ok=True)
            for i, file_path in enumerate(cv_files):
                filename = os.path.basename(file_path)
                status.text(f"Processing {i + 1}/{total}: {filename}")
                try:
                    candidate = parse_cv(file_path)

                    stored_path = os.path.join("uploads/cvs", filename)
                    with open(file_path, "rb") as src, open(stored_path, "wb") as dst:
                        dst.write(src.read())

                    if not candidate.get("name"):
                        error_log.append(f"{filename}: no 'Name' field found — {'; '.join(candidate['warnings'])}")
                        errors += 1
                    elif save_candidate(candidate, cv_path=stored_path, source_filename=filename):
                        saved += 1
                    else:
                        skipped += 1
                except Exception as e:
                    errors += 1
                    error_log.append(f"{filename}: {e}")

                progress_bar.progress((i + 1) / total)

            st.success(f"Import complete — ✅ Saved: {saved}  ⚠️ Duplicates: {skipped}  ❌ Errors/unparsed: {errors}")
            if error_log:
                with st.expander(f"⚠️ {len(error_log)} file(s) need attention"):
                    for line in error_log:
                        st.write("- " + line)
            st.rerun()

st.divider()

# ==========================
# SINGLE CV UPLOAD
# ==========================

st.header("➕ Add a Single CV")

uploaded_file = st.file_uploader("Upload CV", type=["pdf", "docx"])

if uploaded_file:
    os.makedirs("uploads/cvs", exist_ok=True)
    file_path = os.path.join("uploads/cvs", uploaded_file.name)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    candidate = parse_cv(file_path)

    if candidate["warnings"]:
        for w in candidate["warnings"]:
            st.warning(w)

    st.subheader("Extracted Candidate Information")
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Name:** {candidate.get('name') or '—'}")
        st.write(f"**DOB:** {candidate.get('dob') or '—'}")
        st.write(f"**Mobile:** {candidate.get('mobile') or '—'}")
        st.write(f"**Email:** {candidate.get('email') or '—'}")
        st.write(f"**PAN:** {candidate.get('pan_number') or '—'}")
    with col2:
        st.write(f"**Highest Qualification:** {candidate.get('highest_qualification') or '—'}")
        st.write(f"**Latest Designation:** {candidate.get('latest_designation') or '—'}")
        st.write(f"**Total Experience (yrs):** {candidate.get('experience_years', 0)}")
        st.write(f"**Certifications:** {candidate.get('certifications') or '—'}")

    with st.expander("Full parsed detail (qualifications / companies / work history)"):
        st.write("**Qualifications**")
        st.dataframe(pd.DataFrame(candidate["qualifications"]), use_container_width=True)
        st.write("**Companies**")
        st.dataframe(pd.DataFrame(candidate["companies"]), use_container_width=True)
        st.write("**Work History**")
        st.dataframe(pd.DataFrame(candidate["work_history"]), use_container_width=True)

    if st.button("Save Candidate"):
        if save_candidate(candidate, cv_path=file_path, source_filename=uploaded_file.name):
            st.success(f"✅ Saved '{candidate.get('name')}'")
        else:
            st.warning("⚠️ Duplicate — this candidate (matched by PAN, or name+mobile) already exists.")

st.divider()

# ==========================
# CANDIDATE DATABASE
# ==========================

st.header("🗂️ Candidate Database")
candidates = get_candidates()

if not candidates:
    st.info("No candidates in the database yet — import CVs above.")
else:
    display_df = pd.DataFrame([
        {
            "id": c["id"],
            "Name": c["name"],
            "Latest Designation": c["latest_designation"],
            "Highest Qualification": c["highest_qualification"],
            "Experience (yrs)": c["experience_years"],
            "Mobile": c["mobile"],
            "Email": c["email"],
            "State": c["current_state"],
        }
        for c in candidates
    ])

    st.subheader("Filters")
    col1, col2 = st.columns(2)
    with col1:
        designation_filter = st.text_input("Designation contains", placeholder="e.g. bridge engineer, resident engineer...")
        state_filter = st.text_input("State")
    with col2:
        min_experience = st.number_input("Minimum experience (years)", min_value=0, value=0)
        qualification_filter = st.text_input("Qualification contains")

    filtered = display_df.copy()
    if designation_filter:
        filtered = filtered[filtered["Latest Designation"].fillna("").str.contains(designation_filter, case=False, na=False)]
    if state_filter:
        filtered = filtered[filtered["State"].fillna("").str.contains(state_filter, case=False, na=False)]
    if qualification_filter:
        filtered = filtered[filtered["Highest Qualification"].fillna("").str.contains(qualification_filter, case=False, na=False)]
    filtered = filtered[filtered["Experience (yrs)"].fillna(0) >= min_experience]

    st.dataframe(filtered, use_container_width=True, hide_index=True)

    st.subheader("🗑️ Delete a Candidate")
    options = {f"{c['name']} — {c['latest_designation']} (id={c['id']})": c["id"] for c in candidates}
    selected_label = st.selectbox("Select candidate to delete", options=["— select —"] + list(options.keys()))
    if selected_label != "— select —":
        selected_id = options[selected_label]
        st.warning(f"You are about to delete **{selected_label}**. This cannot be undone.")
        if st.button("Confirm Delete"):
            if delete_candidate(selected_id):
                st.success("✅ Deleted.")
                st.rerun()
            else:
                st.error("❌ Could not delete.")

st.divider()
st.caption("For tender/position scoring against these candidates, use the **Tender Evaluator** page in the sidebar.")
