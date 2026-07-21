import pandas as pd
import streamlit as st

from get_candidates import get_candidates
from Coastal_rubrics import COASTAL_PACKAGE_1_IE_RUBRICS
from Rubric_assessments import save_assessment, load_assessment, load_all_assessments

RUBRIC_SOURCE = "coastal_package_1_ie"

st.set_page_config(page_title="Exact CV Scoring", layout="wide")
st.title("📐 Exact CV Scoring — COASTAL Package-1 IE RFP")
st.write(
    "Scores each candidate exactly the way the RFP does — every criterion listed "
    "separately, with its own base-marks-plus-capped-bonus formula (Section VI-A, "
    "pp. 259–277), instead of the earlier 3-bucket weighted-keyword approximation. "
    "Enter the raw value the assessor would claim for each criterion (years, project "
    "count, or whether a qualification item is met) — the exact marks are computed "
    "and totalled automatically."
)

candidates = get_candidates()
if not candidates:
    st.warning("No candidates in the database yet — add CVs on the main dashboard first.")
    st.stop()

candidate_options = {f"{c['name']} (id={c['id']})": c for c in candidates}

col_pos, col_cand = st.columns(2)
with col_pos:
    position_name = st.selectbox("Position", list(COASTAL_PACKAGE_1_IE_RUBRICS.keys()))
with col_cand:
    candidate_label = st.selectbox("Candidate", list(candidate_options.keys()))

rubric = COASTAL_PACKAGE_1_IE_RUBRICS[position_name]
candidate = candidate_options[candidate_label]

if rubric.source_note:
    st.caption(f"Source: {rubric.source_note}")

st.divider()

# ── Load any previously saved raw values for this candidate + position ────
state_key = f"rubric_values_{position_name}_{candidate['id']}"
if state_key not in st.session_state:
    st.session_state[state_key] = load_assessment(RUBRIC_SOURCE, position_name, candidate["id"])
saved_values = st.session_state[state_key]

st.subheader(f"📋 {position_name} — scoring worksheet for {candidate['name']}")
st.caption(
    f"Candidate's parsed data for reference — Total experience: "
    f"{candidate.get('experience_years', 0)} yrs · Latest designation: "
    f"{candidate.get('latest_designation') or '—'} · Highest qualification: "
    f"{candidate.get('highest_qualification') or '—'}"
)

input_values: dict[str, float] = {}

for category in rubric.categories:
    st.markdown(f"#### {category}")
    for c in [c for c in rubric.criteria if c.category == category]:
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.write(f"**{c.label}**")
                st.caption(f"Max {c.max_points:g} marks — {c.scale_description()}")
            with right:
                default = saved_values.get(c.key)
                if c.kind == "flat":
                    checked = st.checkbox(
                        "Met", value=bool(default) if default is not None else False,
                        key=f"input_{position_name}_{candidate['id']}_{c.key}"
                    )
                    input_values[c.key] = 1.0 if checked else 0.0
                else:
                    val = st.number_input(
                        c.unit_label.capitalize() or "Value", min_value=0.0,
                        value=float(default) if default is not None else 0.0, step=0.5,
                        key=f"input_{position_name}_{candidate['id']}_{c.key}"
                    )
                    input_values[c.key] = val
                earned = c.score(input_values[c.key])
                st.metric("Earned", f"{earned:g} / {c.max_points:g}", label_visibility="collapsed")

st.divider()

result = rubric.score(input_values)
st.subheader(f"🏆 Total: {result['total']:g} / {result['max_total']:g}")

if st.button("💾 Save this assessment"):
    save_assessment(RUBRIC_SOURCE, position_name, candidate["id"], input_values)
    st.session_state[state_key] = input_values
    st.success(f"Saved — {candidate['name']} scores {result['total']:g}/100 for {position_name}.")

with st.expander("Full breakdown"):
    breakdown_df = pd.DataFrame([
        {"Category": row["category"], "Criterion": row["label"],
         "Raw value": row["raw_value"], "Earned": row["earned"], "Max": row["max_points"]}
        for row in result["per_criterion"]
    ])
    st.dataframe(breakdown_df, use_container_width=True, hide_index=True)

st.divider()

# ── Ranking across every candidate assessed for this position ─────────────
st.subheader(f"📊 Candidates ranked for {position_name}")
st.caption("Only candidates with a saved assessment for this position appear here.")

all_assessments = load_all_assessments(RUBRIC_SOURCE, position_name)
if not all_assessments:
    st.info("No saved assessments yet for this position — score and save at least one candidate above.")
else:
    candidates_by_id = {c["id"]: c for c in candidates}
    rows = []
    for cand_id, values in all_assessments.items():
        cand = candidates_by_id.get(cand_id)
        if not cand:
            continue
        scored = rubric.score(values)
        rows.append({
            "Candidate": cand["name"],
            "Designation": cand.get("latest_designation") or "—",
            "Total": scored["total"],
        })
    ranking_df = pd.DataFrame(rows).sort_values("Total", ascending=False).reset_index(drop=True)
    ranking_df.insert(0, "Rank", range(1, len(ranking_df) + 1))
    st.dataframe(ranking_df, use_container_width=True, hide_index=True)
