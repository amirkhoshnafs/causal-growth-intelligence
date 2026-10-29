"""Permit numerical unit tests without starting a Streamlit runtime."""
import sys
import types

sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))
