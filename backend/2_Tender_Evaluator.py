import pandas as pd
import streamlit as st

from get_candidates import get_candidates
from tender_requirements import (
    PositionRequirement, score_candidate,
    save_requirement_set, load_requirement_set,
    list_saved_tender_names, delete_requirement_set,
)
from tender_presets import PRESETS, get_preset

st.set_page_config(page_title="Tender Evaluator", layout="wide")
st.title("🎯 Tender Evaluator")
st.write(
    "Type in each position's requirements yourself — qualification and "
    "designation keywords, minimum experience, and point weights — then "
    "score every candidate in the database against them. Nothing is "
    "auto-guessed from an uploaded tender document."
)

if "positions" not in st.session_state:
    st.session_state.positions = [PositionRequirement(position_name="")]

# ── Load a built-in preset (hardcoded, no DB round-trip needed) ─────────
if PRESETS:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        preset_choice = st.selectbox("Load a built-in tender preset", ["— select —"] + list(PRESETS.keys()))
    with col_b:
        st.write("")
        st.write("")
        if preset_choice != "— select —" and st.button("Load preset"):
            st.session_state.positions = get_preset(preset_choice)
            st.session_state.tender_name = preset_choice
            st.rerun()

# ── Load a previously saved (DB) requirement set ─────────────────────────
saved_names = list_saved_tender_names()
if saved_names:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        to_load = st.selectbox("...or load a requirement set you saved earlier", ["— select —"] + saved_names)
    with col_b:
        st.write("")
        st.write("")
        if to_load != "— select —" and st.button("Load saved"):
            st.session_state.positions = load_requirement_set(to_load)
            st.session_state.tender_name = to_load
            st.rerun()

st.divider()

# ── Requirement entry form ──────────────────────────────────────────────
st.subheader("📋 Position Requirements")

tender_name = st.text_input("Tender / requirement-set name", value=st.session_state.get("tender_name", ""),
                             placeholder="e.g. RSRDC Highway Package IE Team")

for i, pos in enumerate(st.session_state.positions):
    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            pos.position_name = st.text_input(f"Position {i + 1} name", value=pos.position_name, key=f"name_{i}")
        with c2:
            if len(st.session_state.positions) > 1 and st.button("Remove", key=f"remove_{i}"):
                st.session_state.positions.pop(i)
                st.rerun()

        pos.min_experience_years = st.number_input(
            "Minimum experience (years)", min_value=0.0, value=float(pos.min_experience_years), key=f"minexp_{i}"
        )
        qual_kw = st.text_input(
            "Qualification keywords (comma-separated — matched against highest qualification & certifications)",
            value=", ".join(pos.qualification_keywords), key=f"qualkw_{i}",
            placeholder="e.g. civil, highway, transportation"
        )
        desig_kw = st.text_input(
            "Designation keywords (comma-separated — matched against all designations held)",
            value=", ".join(pos.designation_keywords), key=f"desigkw_{i}",
            placeholder="e.g. resident engineer, highway engineer, project manager"
        )
        pos.qualification_keywords = [k.strip() for k in qual_kw.split(",") if k.strip()]
        pos.designation_keywords = [k.strip() for k in desig_kw.split(",") if k.strip()]

        st.write("**Point weights** (should add up to 100)")
        w1, w2, w3 = st.columns(3)
        with w1:
            pos.weight_qualification = st.number_input("Qualification", min_value=0.0, max_value=100.0,
                                                         value=float(pos.weight_qualification), key=f"wq_{i}")
        with w2:
            pos.weight_experience = st.number_input("Experience", min_value=0.0, max_value=100.0,
                                                      value=float(pos.weight_experience), key=f"we_{i}")
        with w3:
            pos.weight_designation = st.number_input("Designation", min_value=0.0, max_value=100.0,
                                                       value=float(pos.weight_designation), key=f"wd_{i}")
        total_w = pos.weight_qualification + pos.weight_experience + pos.weight_designation
        if total_w != 100:
            st.caption(f"⚠️ Weights currently sum to {total_w:.0f}, not 100 — scores will be out of {total_w:.0f}.")

col_add, col_save = st.columns([1, 1])
with col_add:
    if st.button("➕ Add another position"):
        st.session_state.positions.append(PositionRequirement(position_name=""))
        st.rerun()
with col_save:
    if tender_name and st.button("💾 Save this requirement set"):
        save_requirement_set(tender_name, st.session_state.positions)
        st.session_state.tender_name = tender_name
        st.success(f"Saved '{tender_name}'.")
        st.rerun()

if tender_name and tender_name in saved_names:
    if st.button("🗑️ Delete this saved requirement set"):
        delete_requirement_set(tender_name)
        st.success(f"Deleted '{tender_name}'.")
        st.rerun()

st.divider()

# ── Scoring ──────────────────────────────────────────────────────────────
st.subheader("🏆 Candidate Rankings by Position")

candidates = get_candidates()
if not candidates:
    st.warning("No candidates in the database yet — add CVs on the main dashboard first.")
    st.stop()

positions = [p for p in st.session_state.positions if p.position_name.strip()]
if not positions:
    st.info("Add at least one position with a name above to see rankings.")
    st.stop()

position_matches: dict[str, list[dict]] = {}
coverage_data = []

for pos in positions:
    st.markdown(f"### {pos.position_name}")

    matches = []
    for c in candidates:
        breakdown = score_candidate(c, pos)
        if breakdown["total"] > 0:
            matches.append({
                "name": c["name"],
                "designation": c["latest_designation"],
                "experience": c["experience_years"],
                "qualification": c["highest_qualification"],
                "score": breakdown["total"],
                "qualification_score": breakdown["qualification_score"],
                "experience_score": breakdown["experience_score"],
                "designation_score": breakdown["designation_score"],
            })

    matches = sorted(matches, key=lambda x: (x["score"], x["experience"]), reverse=True)
    position_matches[pos.position_name] = matches

    if matches:
        coverage_data.append({
            "Position": pos.position_name,
            "Candidates Found": len(matches),
            "Best Candidate": matches[0]["name"],
            "Best Score": matches[0]["score"],
        })
        ranked_df = pd.DataFrame(matches).head(15)
        ranked_df.insert(0, "Rank", range(1, len(ranked_df) + 1))
        st.dataframe(
            ranked_df[["Rank", "name", "designation", "experience", "qualification",
                       "score", "qualification_score", "experience_score", "designation_score"]],
            use_container_width=True, hide_index=True,
        )
    else:
        st.warning("No matching candidates found — try broadening the keywords or lowering minimum experience.")

st.divider()

# ── Coverage summary ─────────────────────────────────────────────────────
st.subheader("📈 Tender Coverage Summary")
if coverage_data:
    st.dataframe(pd.DataFrame(coverage_data), use_container_width=True, hide_index=True)
else:
    st.info("No coverage data available.")

st.divider()

# ── Recommended team (one distinct person per position) ─────────────────
st.subheader("✅ Recommended Tender Team")

assigned_names = set()
recommended_team = []
position_order = sorted(
    position_matches.keys(),
    key=lambda p: (position_matches[p][0]["score"] if position_matches[p] else -1),
    reverse=True,
)

unfilled_positions = []
for position_label in position_order:
    candidates_for_pos = position_matches.get(position_label, [])
    chosen = next((c for c in candidates_for_pos if c["name"] not in assigned_names), None)
    if chosen:
        assigned_names.add(chosen["name"])
        recommended_team.append({
            "Position": position_label,
            "Candidate": chosen["name"],
            "Designation": chosen["designation"],
            "Experience": chosen["experience"],
            "Score": chosen["score"],
        })
    else:
        unfilled_positions.append(position_label)

if recommended_team:
    position_names = [p.position_name for p in positions]
    team_df = pd.DataFrame(recommended_team)
    team_df["__order"] = team_df["Position"].apply(lambda p: position_names.index(p) if p in position_names else 999)
    team_df = team_df.sort_values("__order").drop(columns="__order")
    st.dataframe(team_df, use_container_width=True, hide_index=True)
if unfilled_positions:
    st.warning("No remaining eligible candidate for: " + ", ".join(unfilled_positions)
               + " (all qualified matches were already assigned to other positions).")
if not recommended_team and not unfilled_positions:
    st.warning("No recommended team could be formed.")
