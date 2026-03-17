import json
import streamlit as st
from pathlib import Path


def load_profiles() -> dict:
    """Load user profiles from JSON."""
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "evals" / "user_profiles.json",
        Path("evals/user_profiles.json"),
    ]
    for path in candidates:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    return {
        "rohan": {"name": "Rohan", "description": "Default user"},
        "meera": {"name": "Meera", "description": "Working professional"},
        "priya": {"name": "Priya", "description": "College student"},
        "testuser_b": {"name": "TestUser_B", "description": "Isolation testing"},
    }


def render_user_switcher():
    """Render user profile switcher in the sidebar."""
    profiles = load_profiles()
    profile_names = {pid: p.get("name", pid) for pid, p in profiles.items()}

    current = st.session_state.get("current_user", "rohan")

    selected = st.selectbox(
        "Active User",
        options=list(profile_names.keys()),
        format_func=lambda x: profile_names[x],
        index=list(profile_names.keys()).index(current) if current in profile_names else 0,
        key="user_selector",
    )

    if selected != current:
        st.session_state.current_user = selected
        st.session_state.pop("last_debug", None)
        st.session_state.pop("last_live_score", None)
        st.toast(f"Switched to {profile_names[selected]}")
        st.rerun()

    profile = profiles.get(selected, {})
    with st.expander("Profile Details", expanded=False):
        st.caption(profile.get("description", "No description"))
        if profile.get("age"):
            st.caption(f"Age: {profile['age']} | City: {profile.get('city', '?')}")
