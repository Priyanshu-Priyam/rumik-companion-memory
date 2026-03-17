from __future__ import annotations
import streamlit as st


def render_chat_panel():
    """Render the main chat panel with message history and input."""
    st.markdown("### Chat with Ira")

    if "messages" not in st.session_state:
        st.session_state.messages = {}

    if "turn_debug_history" not in st.session_state:
        st.session_state.turn_debug_history = {}

    user_id = st.session_state.get("current_user", "rohan")
    if user_id not in st.session_state.messages:
        st.session_state.messages[user_id] = []
    if user_id not in st.session_state.turn_debug_history:
        st.session_state.turn_debug_history[user_id] = []

    user_messages = st.session_state.messages[user_id]
    turn_debugs = st.session_state.turn_debug_history[user_id]

    chat_container = st.container(height=500)
    with chat_container:
        for i, msg in enumerate(user_messages):
            role = msg["role"]
            content = msg["content"]
            if role == "user":
                with st.chat_message("user", avatar="👤"):
                    st.markdown(content)
            else:
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(content)
                    live_score = msg.get("live_score")
                    if live_score:
                        overall = live_score.get("overall", 0)
                        _render_inline_score(overall, live_score)

    if prompt := st.chat_input("Type your message...", key="chat_input"):
        user_messages.append({"role": "user", "content": prompt})

        brain = st.session_state.get("brain")
        if brain is None:
            user_messages.append({
                "role": "assistant",
                "content": "Brain not initialized. Check your configuration.",
            })
            st.rerun()
            return

        history_for_brain = [
            {"role": m["role"], "content": m["content"]}
            for m in user_messages[:-1]
        ]

        with st.spinner("Ira is thinking..."):
            result = brain.chat(
                user_id=user_id,
                message=prompt,
                history=history_for_brain,
            )

        response = result.get("response", "Something went wrong.")
        debug = result.get("debug", {})

        live_score = None
        brain_choice = st.session_state.get("brain_choice", "")
        if "Brain B" in brain_choice:
            try:
                from rumik.chat.live_scorer import score_response
                with st.spinner("Scoring response..."):
                    live_score = score_response(
                        response, prompt, debug,
                        history=history_for_brain,
                    )
            except Exception as e:
                live_score = {"overall": 0.0, "breakdown": {}, "flags": [str(e)], "judge_reasoning": "Scorer error"}

        user_messages.append({
            "role": "assistant",
            "content": response,
            "live_score": live_score,
        })

        st.session_state["last_debug"] = debug
        st.session_state["last_live_score"] = live_score

        turn_debugs.append({
            "turn": len(turn_debugs) + 1,
            "user_message": prompt,
            "response": response[:100],
            "extractions": debug.get("extractions", []),
            "extraction_error": debug.get("extraction_error"),
            "manager_actions": debug.get("manager_actions", []),
            "retrieved_count": len(debug.get("retrieved_facts", [])),
            "withheld_sensitive": debug.get("withheld_sensitive", 0),
            "has_relevant_facts": debug.get("has_relevant_facts"),
            "live_score": live_score.get("overall") if live_score else None,
        })

        st.rerun()


def _render_inline_score(overall: float, live_score: dict):
    """Render a compact quality badge under the response."""
    if overall >= 0.8:
        color = "green"
        label = "Good"
    elif overall >= 0.6:
        color = "orange"
        label = "Fair"
    else:
        color = "red"
        label = "Needs Work"

    st.caption(f"Quality: :{color}[**{label}** ({overall:.0%})]")
    flags = live_score.get("flags", [])
    if flags:
        for flag in flags[:3]:
            st.caption(f"  :orange[{flag}]")
