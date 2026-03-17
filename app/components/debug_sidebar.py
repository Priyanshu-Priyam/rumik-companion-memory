from __future__ import annotations
import json
from pathlib import Path
import streamlit as st


def render_debug_sidebar():
    """Full pipeline debug view — shows live memory state, per-turn trace, and eval scores."""
    st.markdown("---")

    tab_debug, tab_memory, tab_score = st.tabs(["Pipeline", "Memory Store", "Live Scores"])

    with tab_debug:
        _render_pipeline_tab()
    with tab_memory:
        _render_memory_store_tab()
    with tab_score:
        _render_live_scores_tab()


def _render_pipeline_tab():
    """Per-turn pipeline debug: extractions, actions, retrieval, policies, prompt."""
    st.markdown("#### Pipeline Debug")

    debug = st.session_state.get("last_debug", {})
    if not debug:
        st.caption("Send a message to see pipeline internals.")
        return

    model_used = debug.get("model_id", "default")
    st.caption(f"Model: `{model_used or 'config default'}`")

    # --- Extraction error alert ---
    ext_error = debug.get("extraction_error")
    if ext_error:
        st.error(f"Extraction failed: {ext_error}")

    ext_source = debug.get("extraction_source", "")
    if ext_source and ext_source not in ("llm", "greeting_skip", "empty"):
        st.warning(f"Extraction source: **{ext_source}**")

    # --- Write phase: Extractions ---
    extractions = debug.get("extractions")
    if extractions is not None:
        if extractions:
            st.success(f"Extracted {len(extractions)} fact(s)")
            for ext in extractions:
                ext_type = ext.get("type", "?")
                pred = ext.get("predicate", "?")
                val = ext.get("value", "?")
                old = ext.get("old_value")
                sens = ext.get("sensitivity", "none")
                icon = _type_icon(ext_type)
                line = f"{icon} **{ext_type}**: `{pred}` = `{val}`"
                if old:
                    line += f" _(was: {old})_"
                if sens and sens != "none":
                    line += f" 🔒{sens}"
                st.markdown(line)
        elif not ext_error:
            st.info("No facts extracted from this message")
    elif debug.get("facts_used") is not None:
        st.info("Brain A — no extraction pipeline")

    # --- Write phase: Manager Actions ---
    actions = debug.get("manager_actions")
    if actions:
        st.markdown(f"**Memory Writes ({len(actions)})**")
        for a in actions:
            action = a.get("action", "?")
            pred = a.get("predicate", "?")
            val = a.get("new_value") or a.get("value", "?")
            icon = _action_icon(action)
            line = f"{icon} `{action}` → `{pred}` = `{val}`"
            old = a.get("old_value")
            if old:
                line += f" _(was: {old})_"
            st.markdown(line)

    st.markdown("---")

    # --- Read phase: Retrieved facts ---
    retrieved = debug.get("retrieved_facts")
    if retrieved is not None:
        with st.expander(f"Retrieved Facts ({len(retrieved)})", expanded=True):
            if retrieved:
                for f in retrieved[:15]:
                    score = f.get("score") or 0
                    pred = f.get("predicate", "?")
                    val = f.get("value", "?")
                    status = f.get("status", "current")
                    sens = f.get("sensitivity", "none")
                    bar = _score_bar(score)
                    lock = " 🔒" if sens in ("high", "intimate") else ""
                    st.markdown(f"`{bar}` **{pred}**: {val} _({status})_{lock}")
            else:
                st.caption("No facts retrieved for this query.")

    # --- Read phase: Policy summary ---
    has_relevant = debug.get("has_relevant_facts")
    if has_relevant is not None:
        withheld = debug.get("withheld_sensitive", 0)
        historical = debug.get("historical_count", 0)
        cols = st.columns(3)
        cols[0].metric("Relevant", "Yes" if has_relevant else "No")
        cols[1].metric("Withheld", withheld)
        cols[2].metric("Historical", historical)

    # --- Raw facts dump (Brain A) ---
    facts_used = debug.get("facts_used")
    if facts_used is not None and retrieved is None:
        with st.expander(f"Brain A Memory ({len(facts_used)} facts)", expanded=False):
            for f in facts_used:
                key = f.get("key", "?")
                value = f.get("value", "?")
                sensitive = f.get("sensitive", False)
                marker = " 🔒" if sensitive else ""
                st.text(f"• {key}: {value}{marker}")

    # --- Extraction raw response (debug) ---
    ext_raw = debug.get("extraction_raw")
    if ext_raw:
        with st.expander("Extraction Raw Response", expanded=False):
            st.code(ext_raw, language="json")

    # --- System prompt ---
    with st.expander("System Prompt", expanded=False):
        system_prompt = debug.get("system_prompt", "N/A")
        st.code(system_prompt, language=None)

    # --- Turn history ---
    user_id = st.session_state.get("current_user", "rohan")
    turn_debugs = st.session_state.get("turn_debug_history", {}).get(user_id, [])
    if turn_debugs:
        with st.expander(f"Turn History ({len(turn_debugs)} turns)", expanded=False):
            for td in reversed(turn_debugs):
                ext_count = len(td.get("extractions", []))
                act_count = len(td.get("manager_actions", []))
                retr = td.get("retrieved_count", 0)
                with_s = td.get("withheld_sensitive", 0)
                ext_err = td.get("extraction_error")
                score_val = td.get("live_score")
                score_str = f" | Score: {score_val:.0%}" if score_val is not None else ""
                err_str = f" | ERR: {ext_err[:40]}" if ext_err else ""
                st.markdown(
                    f"**Turn {td['turn']}**: _{td['user_message'][:50]}_\n"
                    f"  Extracted: {ext_count} | Writes: {act_count} | "
                    f"Retrieved: {retr} | Withheld: {with_s}{score_str}{err_str}"
                )


def _render_memory_store_tab():
    """Live view of all facts currently in the memory store for this user."""
    st.markdown("#### Live Memory Store")

    brain = st.session_state.get("brain")
    user_id = st.session_state.get("current_user", "rohan")

    if brain is None:
        st.caption("No brain initialized.")
        return

    store = getattr(brain, "_store", None)
    if store is None:
        st.info("Brain A has no structured memory store. Facts are seeded per-turn into the prompt.")
        facts_used = st.session_state.get("last_debug", {}).get("facts_used")
        if facts_used:
            for f in facts_used:
                st.text(f"• {f.get('key', '?')}: {f.get('value', '?')}")
        return

    if st.button("Refresh Memory", key="refresh_mem"):
        pass

    all_facts = store.get_all_facts(user_id)
    if not all_facts:
        st.caption("No facts stored for this user yet. Start chatting to build memory!")
        return

    current = [f for f in all_facts if f.get("status") == "current"]
    corrected = [f for f in all_facts if f.get("status") == "corrected"]
    stale = [f for f in all_facts if f.get("status") == "stale"]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", len(all_facts))
    c2.metric("Current", len(current))
    c3.metric("Corrected", len(corrected))
    c4.metric("Stale", len(stale))

    if current:
        st.markdown("**Current Facts**")
        for f in current:
            sens = f.get("sensitivity", "none")
            lock = " 🔒" if sens in ("high", "intimate") else ""
            sup = f" _(supersedes: {f['supersedes'][:8]}...)_" if f.get("supersedes") else ""
            st.markdown(f"- `{f['predicate']}`: **{f['value']}**{lock}{sup}")

    if corrected:
        with st.expander(f"Corrected ({len(corrected)})", expanded=False):
            for f in corrected:
                st.markdown(f"- ~~`{f['predicate']}`: {f['value']}~~")

    if stale:
        with st.expander(f"Stale ({len(stale)})", expanded=False):
            for f in stale:
                st.markdown(f"- `{f['predicate']}`: {f['value']} _(stale)_")


def _render_live_scores_tab():
    """Show real-time eval scores from the live chat session."""
    st.markdown("#### Live Quality Scores")

    brain_choice = st.session_state.get("brain_choice", "")
    if "Brain A" in brain_choice:
        st.info("Live scoring is available for Brain B only. Switch to Brain B to see scores.")
        return

    live_score = st.session_state.get("last_live_score")
    if not live_score:
        st.caption("Send a message with Brain B to see live quality scores.")
        return

    # --- Overall score ---
    overall = live_score.get("overall", 0)
    if overall >= 0.8:
        st.success(f"Overall Quality: **{overall:.0%}**")
    elif overall >= 0.6:
        st.warning(f"Overall Quality: **{overall:.0%}**")
    else:
        st.error(f"Overall Quality: **{overall:.0%}**")

    # --- Breakdown ---
    breakdown = live_score.get("breakdown", {})
    if breakdown:
        st.markdown("**Score Breakdown**")
        dim_labels = {
            "extraction": "Extraction",
            "memory_utilization": "Memory Use",
            "sensitivity": "Sensitivity",
            "honesty": "Honesty",
            "quality": "Response Quality",
            "llm_judge": "LLM Judge",
        }
        for key, label in dim_labels.items():
            val = breakdown.get(key)
            if val is not None:
                bar = _score_bar(val)
                st.markdown(f"`{bar}` **{label}**: {val:.0%}")

    # --- Flags ---
    flags = live_score.get("flags", [])
    if flags:
        st.markdown("**Warnings**")
        for flag in flags:
            st.caption(f":orange[{flag}]")
    else:
        st.caption("No quality warnings")

    # --- Judge reasoning ---
    reasoning = live_score.get("judge_reasoning", "")
    if reasoning:
        with st.expander("Judge Reasoning", expanded=False):
            st.markdown(reasoning)

    # --- Session trend ---
    user_id = st.session_state.get("current_user", "rohan")
    turn_debugs = st.session_state.get("turn_debug_history", {}).get(user_id, [])
    scores = [td.get("live_score") for td in turn_debugs if td.get("live_score") is not None]
    if len(scores) >= 2:
        st.markdown("**Session Trend**")
        avg = sum(scores) / len(scores)
        st.caption(f"Avg: {avg:.0%} over {len(scores)} turns | Latest: {scores[-1]:.0%}")
        trend = "improving" if len(scores) >= 3 and scores[-1] > scores[-3] else "stable"
        st.caption(f"Trend: {trend}")


def _type_icon(ext_type: str) -> str:
    return {
        "new_fact": "🆕",
        "correction": "✏️",
        "temporal_update": "⏱️",
        "entity_disambiguation": "🔀",
        "emotional_context": "💭",
    }.get(ext_type, "📝")


def _action_icon(action: str) -> str:
    return {
        "added": "✅",
        "corrected": "✏️",
        "temporal_update": "⏱️",
        "disambiguated": "🔀",
        "skipped_duplicate": "⏭️",
        "error": "❌",
    }.get(action, "📝")


def _score_bar(score: float) -> str:
    filled = int(score * 5)
    return "█" * filled + "░" * (5 - filled)
