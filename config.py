import streamlit as st

YOUTUBE_API_KEY = st.secrets.get("YOUTUBE_API_KEY", "")
NVIDIA_API_KEY = st.secrets.get("NVIDIA_API_KEY", "")

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"