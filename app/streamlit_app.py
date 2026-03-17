import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from rumik.config import Cfg
from rumik.baseline.engine import BaselineEngine
from app.components.chat_panel import render_chat_panel
from app.components.user_switcher import render_user_switcher
from app.components.debug_sidebar import render_debug_sidebar

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "rumik.db"

st.set_page_config(
    page_title="Ira – Companion Chat",
    page_icon="💬",
    layout="wide",
)


def _create_brain(brain_choice: str, model_id: str):
    """Create a fresh brain instance."""
    DATA_DIR.mkdir(exist_ok=True)
    if "Brain A" in brain_choice:
        return BaselineEngine(model_id=model_id)
    else:
        from rumik.chat.engine import ImprovedEngine
        return ImprovedEngine(
            model_id=model_id,
            extract_on_chat=True,
            db_path=str(DB_PATH),
        )


def _nuclear_clear():
    """Full reset: wipe database file, destroy brain, clear all state."""
    if DB_PATH.exists():
        os.remove(str(DB_PATH))

    st.session_state.messages = {}
    st.session_state.turn_debug_history = {}
    st.session_state.pop("last_debug", None)
    st.session_state.pop("last_live_score", None)
    st.session_state.pop("brain", None)
    st.session_state.pop("_brain_key", None)


# --- Sidebar ---
with st.sidebar:
    st.title("Ira Companion")
    st.caption("Memory-augmented AI companion")
    st.markdown("---")

    brain_options = ["Brain A (Baseline)"]
    improved_available = False
    try:
        from rumik.chat.engine import ImprovedEngine
        brain_options.append("Brain B (Improved)")
        improved_available = True
    except ImportError:
        pass

    brain_choice = st.selectbox("Brain", brain_options, key="brain_choice")

    model_names = list(Cfg.AVAILABLE_MODELS.keys())
    selected_model_name = st.selectbox(
        "Model",
        model_names,
        index=0,
        key="model_selector",
    )
    selected_model_id = Cfg.AVAILABLE_MODELS[selected_model_name]
    st.caption(f"`{selected_model_id}`")

    st.markdown("---")

    render_user_switcher()

    # --- Brain creation / recreation ---
    current_brain_key = f"{brain_choice}_{selected_model_id}"
    if st.session_state.get("_brain_key") != current_brain_key:
        st.session_state.brain = _create_brain(brain_choice, selected_model_id)
        st.session_state._brain_key = current_brain_key

    # --- Clear button: nuclear reset ---
    if st.button("Clear Chat & Memory", use_container_width=True, type="primary"):
        _nuclear_clear()
        st.rerun()

    render_debug_sidebar()

# --- Main Panel ---
render_chat_panel()
