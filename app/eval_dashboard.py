"""Eval Dashboard — side-by-side Brain A vs Brain B case explorer.

Run:  python3.9 -m streamlit run app/eval_dashboard.py
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Eval Dashboard — Rumik",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent.parent


# ── Data Loading ────────────────────────────────────────────────────────────


@st.cache_data
def load_data():
    suite_path = ROOT / "golden_suite.jsonl"
    base_path = ROOT / "results" / "baseline.json"
    imp_path = ROOT / "results" / "improved.json"

    cases = {}
    with open(suite_path) as f:
        for line in f:
            c = json.loads(line)
            cases[c["id"]] = c

    base_results = {}
    if base_path.exists():
        with open(base_path) as f:
            for r in json.load(f)["results"]:
                base_results[r["case_id"]] = r

    imp_results = {}
    if imp_path.exists():
        with open(imp_path) as f:
            for r in json.load(f)["results"]:
                imp_results[r["case_id"]] = r

    return cases, base_results, imp_results


# ── Helpers ─────────────────────────────────────────────────────────────────


def status_icon(passed):
    if passed is None:
        return "—"
    return "✅" if passed else "❌"


def delta_label(base_passed, imp_passed):
    if base_passed is None or imp_passed is None:
        return "—"
    if base_passed and not imp_passed:
        return "🔻 Regression"
    if not base_passed and imp_passed:
        return "🔺 Improvement"
    if base_passed and imp_passed:
        return "✅ Both Pass"
    return "❌ Both Fail"


def severity_color(sev):
    return {"critical": "🔴", "high": "🟠", "medium": "🟡"}.get(sev, "⚪")


# ── Render Functions ────────────────────────────────────────────────────────


def render_result(result):
    """Render a single brain's result for a case."""
    if not result:
        st.info("No result available.")
        return

    passed = result.get("passed")
    score = result.get("score", 0)

    if passed:
        st.success(f"PASSED — Score: {score:.2f}")
    else:
        st.error(f"FAILED — Score: {score:.2f}")

    if result.get("error"):
        st.error(f"Error: {result['error']}")

    st.markdown("**Response:**")
    response_text = result.get("response", "—")
    border_color = "#4caf50" if passed else "#f44336"
    st.markdown(
        f'<div style="padding: 12px; border-radius: 8px; '
        f'border-left: 4px solid {border_color}; '
        f'background-color: rgba(128,128,128,0.08); '
        f'margin-bottom: 12px; white-space: pre-wrap;">{response_text}</div>',
        unsafe_allow_html=True,
    )

    rc = result.get("rule_checks")
    if rc:
        rc_label = f"Rule Checks ({rc.get('checks_passed', 0)}/{rc.get('checks_total', 0)} passed)"
        with st.expander(rc_label, expanded=not rc.get("passed", True)):
            st.write(f"**Score:** {rc.get('score', 0):.2f}")
            failures = rc.get("failures", [])
            if failures:
                st.markdown("**Failures:**")
                for fail in failures:
                    st.markdown(f"- ❌ {fail}")
            else:
                st.markdown("All rule checks passed.")

    ja = result.get("judge_assessment")
    if ja:
        ja_label = f"LLM Judge ({'PASS' if ja.get('passed') else 'FAIL'} — {ja.get('score', 0):.2f})"
        with st.expander(ja_label, expanded=not ja.get("passed", True)):
            st.markdown(f"**Reasoning:** {ja.get('reasoning', '—')}")
            cs = ja.get("criteria_scores", {})
            if cs:
                score_cols = st.columns(min(len(cs), 4))
                for i, (k, v) in enumerate(cs.items()):
                    score_cols[i % len(score_cols)].metric(
                        k.replace("_", " ").title(),
                        f"{v:.2f}" if isinstance(v, (int, float)) else str(v),
                    )

    debug = result.get("debug")
    if debug:
        _render_pipeline_debug(debug)


def _render_pipeline_debug(debug: dict):
    """Render Brain B pipeline internals: retrieval, extraction, policies, prompt."""
    with st.expander("Pipeline Debug (internals)", expanded=False):
        col_a, col_b = st.columns(2)

        with col_a:
            retrieved = debug.get("retrieved_facts", [])
            st.markdown(f"**Retrieved Facts ({len(retrieved)})**")
            if retrieved:
                for f in retrieved[:20]:
                    score = f.get("score", 0)
                    pred = f.get("predicate", "?")
                    val = f.get("value", "?")
                    status = f.get("status", "current")
                    st.text(f"[{score:.3f}] {pred}: {val} ({status})")
            else:
                st.caption("No facts retrieved.")

            st.markdown("---")

            extractions = debug.get("extractions", [])
            st.markdown(f"**Extractions ({len(extractions)})**")
            if extractions:
                for ext in extractions:
                    etype = ext.get("type", "?")
                    pred = ext.get("predicate", "?")
                    val = ext.get("value", "?")
                    old = ext.get("old_value")
                    if old:
                        st.text(f"{etype}: {pred} = {val} (was: {old})")
                    else:
                        st.text(f"{etype}: {pred} = {val}")
            else:
                st.caption("No extractions (write phase disabled or no facts found).")

        with col_b:
            actions = debug.get("manager_actions", [])
            st.markdown(f"**Memory Actions ({len(actions)})**")
            if actions:
                for a in actions:
                    act = a.get("action", "?")
                    pred = a.get("predicate", "?")
                    val = a.get("new_value") or a.get("value", "?")
                    st.text(f"{act}: {pred} = {val}")
            else:
                st.caption("No memory writes.")

            st.markdown("---")

            st.markdown("**Policy Decisions**")
            has_rel = debug.get("has_relevant_facts")
            withheld = debug.get("withheld_sensitive", 0)
            hist = debug.get("historical_count", 0)
            model = debug.get("model_id", "default")
            st.text(f"Relevant facts: {'Yes' if has_rel else 'No'}")
            st.text(f"Withheld (sensitive): {withheld}")
            st.text(f"Historical loaded: {hist}")
            st.text(f"Model: {model or 'config default'}")

        sys_prompt = debug.get("system_prompt", "")
        if sys_prompt:
            with st.expander("System Prompt", expanded=False):
                st.code(sys_prompt, language=None)


def render_case_detail(case, base_r, imp_r):
    """Render the full detail view for a single eval case."""

    # --- Meta ---
    meta_cols = st.columns(4)
    meta_cols[0].markdown(f"**User Profile:** `{case.get('user_profile', '—')}`")
    meta_cols[1].markdown(
        f"**Severity:** {severity_color(case['severity'])} {case['severity']}"
    )
    meta_cols[2].markdown(f"**Scoring:** `{case.get('scoring', '—')}`")
    tags = ", ".join(case.get("tags", []))
    meta_cols[3].markdown(f"**Tags:** {tags or '—'}")

    # --- Memory State ---
    memory = case.get("memory_state", [])
    if memory:
        st.markdown("#### Memory State")
        mem_header = st.columns([3, 4, 1, 2, 2])
        mem_header[0].markdown("**Key**")
        mem_header[1].markdown("**Value**")
        mem_header[2].markdown("**Conf.**")
        mem_header[3].markdown("**Source**")
        mem_header[4].markdown("**Extra**")
        for m in memory:
            row = st.columns([3, 4, 1, 2, 2])
            row[0].code(m.get("key", ""), language=None)
            row[1].write(m.get("value", ""))
            row[2].write(str(m.get("confidence", "")))
            row[3].write(m.get("source", ""))
            extras = []
            if m.get("sensitive"):
                extras.append("🔒 sensitive")
            if m.get("supersedes"):
                extras.append(f"↩ supersedes: {m['supersedes']}")
            if m.get("superseded"):
                extras.append(f"↩ superseded: {m['superseded']}")
            if m.get("timestamp"):
                extras.append(f"🕐 {m['timestamp']}")
            if m.get("unit"):
                extras.append(f"📏 {m['unit']}")
            row[4].write(" | ".join(extras) if extras else "—")

    # --- Conversation History ---
    history = case.get("history", [])
    if history:
        st.markdown("#### Conversation History")
        for turn in history:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "user":
                st.chat_message("user").write(content)
            else:
                st.chat_message("assistant").write(content)

    # --- Latest User Message ---
    user_msg = case.get("user_message", "")
    if user_msg:
        st.markdown("#### Latest User Message")
        st.chat_message("user").markdown(f"**{user_msg}**")

    # --- Expected / Disallowed ---
    exp_col, dis_col = st.columns(2)
    with exp_col:
        st.markdown("#### Expected Behavior")
        for item in case.get("expected_checks", []):
            st.markdown(f"- ✅ {item}")
    with dis_col:
        st.markdown("#### Disallowed Behavior")
        for item in case.get("disallowed_behaviors", []):
            st.markdown(f"- 🚫 {item}")

    # --- Brain A vs Brain B ---
    st.markdown("---")
    st.markdown("#### Results Comparison")
    a_col, b_col = st.columns(2)

    with a_col:
        st.markdown("##### Brain A (Baseline)")
        render_result(base_r)

    with b_col:
        st.markdown("##### Brain B (Improved)")
        render_result(imp_r)


# ── Main App ────────────────────────────────────────────────────────────────


def main():
    cases, base_results, imp_results = load_data()
    case_ids = sorted(cases.keys(), key=lambda x: (cases[x]["category"], x))

    # ── Sidebar Filters ─────────────────────────────────────────────────
    with st.sidebar:
        st.title("Eval Dashboard")
        st.caption(f"{len(cases)} cases loaded")
        st.markdown("---")

        categories = ["All"] + sorted(set(c["category"] for c in cases.values()))
        sel_cat = st.selectbox("Category", categories)

        severities = ["All"] + sorted(set(c["severity"] for c in cases.values()))
        sel_sev = st.selectbox("Severity", severities)

        status_options = [
            "All",
            "Both Pass",
            "Both Fail",
            "Regression",
            "Improvement",
        ]
        sel_status = st.selectbox("Status", status_options)

        search = st.text_input("Search Case ID", "")

        st.markdown("---")
        st.markdown("**Quick Stats**")
        base_pass = sum(1 for r in base_results.values() if r["passed"])
        imp_pass = sum(1 for r in imp_results.values() if r["passed"])
        regressions = sum(
            1
            for cid in cases
            if base_results.get(cid, {}).get("passed")
            and not imp_results.get(cid, {}).get("passed")
        )
        improvements = sum(
            1
            for cid in cases
            if not base_results.get(cid, {}).get("passed")
            and imp_results.get(cid, {}).get("passed")
        )
        st.metric("Brain A Pass", f"{base_pass}/{len(cases)}")
        st.metric("Brain B Pass", f"{imp_pass}/{len(cases)}")
        st.metric("Regressions", regressions)
        st.metric("Improvements", improvements)

    # ── Filter ──────────────────────────────────────────────────────────
    filtered_ids = []
    for cid in case_ids:
        c = cases[cid]
        if sel_cat != "All" and c["category"] != sel_cat:
            continue
        if sel_sev != "All" and c["severity"] != sel_sev:
            continue
        if search and search.upper() not in cid.upper():
            continue

        bp = base_results.get(cid, {}).get("passed")
        ip = imp_results.get(cid, {}).get("passed")
        dl = delta_label(bp, ip)

        if sel_status == "Both Pass" and dl != "✅ Both Pass":
            continue
        if sel_status == "Both Fail" and dl != "❌ Both Fail":
            continue
        if sel_status == "Regression" and "Regression" not in dl:
            continue
        if sel_status == "Improvement" and "Improvement" not in dl:
            continue

        filtered_ids.append(cid)

    # ── Summary Bar ─────────────────────────────────────────────────────
    st.markdown("# Eval Dashboard — Brain A vs Brain B")

    col1, col2, col3, col4, col5 = st.columns(5)

    base_rate = base_pass / max(len(cases), 1)
    imp_rate = imp_pass / max(len(cases), 1)

    col1.metric("Brain A Pass Rate", f"{base_rate:.1%}")
    col2.metric(
        "Brain B Pass Rate", f"{imp_rate:.1%}", delta=f"{imp_rate - base_rate:+.1%}"
    )

    base_crit = [
        r
        for r in base_results.values()
        if cases.get(r["case_id"], {}).get("severity") == "critical"
    ]
    imp_crit = [
        r
        for r in imp_results.values()
        if cases.get(r["case_id"], {}).get("severity") == "critical"
    ]
    base_crit_rate = sum(1 for r in base_crit if r["passed"]) / max(len(base_crit), 1)
    imp_crit_rate = sum(1 for r in imp_crit if r["passed"]) / max(len(imp_crit), 1)
    col3.metric("Brain A Critical", f"{base_crit_rate:.1%}")
    col4.metric(
        "Brain B Critical",
        f"{imp_crit_rate:.1%}",
        delta=f"{imp_crit_rate - base_crit_rate:+.1%}",
    )
    col5.metric("Showing", f"{len(filtered_ids)}/{len(cases)} cases")

    # ── Category Breakdown ──────────────────────────────────────────────
    with st.expander("Category Breakdown", expanded=True):
        cat_names = sorted(set(c["category"] for c in cases.values()))

        header_cols = st.columns([3, 1, 1, 1, 1, 1, 1])
        header_cols[0].markdown("**Category**")
        header_cols[1].markdown("**Total**")
        header_cols[2].markdown("**A Pass**")
        header_cols[3].markdown("**A Rate**")
        header_cols[4].markdown("**B Pass**")
        header_cols[5].markdown("**B Rate**")
        header_cols[6].markdown("**Delta**")

        for cat in cat_names:
            cat_cases = [cid for cid in cases if cases[cid]["category"] == cat]
            total = len(cat_cases)
            a_pass = sum(
                1
                for cid in cat_cases
                if base_results.get(cid, {}).get("passed")
            )
            b_pass = sum(
                1
                for cid in cat_cases
                if imp_results.get(cid, {}).get("passed")
            )
            a_rate = a_pass / max(total, 1)
            b_rate = b_pass / max(total, 1)
            diff = b_pass - a_pass

            cols = st.columns([3, 1, 1, 1, 1, 1, 1])
            cols[0].write(cat.replace("_", " ").title())
            cols[1].write(str(total))
            cols[2].write(str(a_pass))
            cols[3].write(f"{a_rate:.0%}")
            cols[4].write(str(b_pass))
            cols[5].write(f"{b_rate:.0%}")
            if diff > 0:
                cols[6].write(f"🔺 +{diff}")
            elif diff < 0:
                cols[6].write(f"🔻 {diff}")
            else:
                cols[6].write("—")

    # ── Case List ───────────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(f"### Cases ({len(filtered_ids)})")

    for cid in filtered_ids:
        c = cases[cid]
        br = base_results.get(cid, {})
        ir = imp_results.get(cid, {})

        bp = br.get("passed")
        ip = ir.get("passed")
        bs = br.get("score", 0)
        is_ = ir.get("score", 0)
        dl = delta_label(bp, ip)

        sev_icon = severity_color(c["severity"])
        title = (
            f"{sev_icon} **{cid}** — "
            f"{c['category'].replace('_', ' ').title()} | "
            f"A: {status_icon(bp)} {bs:.2f}  "
            f"B: {status_icon(ip)} {is_:.2f}  | {dl}"
        )

        with st.expander(title, expanded=False):
            render_case_detail(c, br, ir)


main()
