import os

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY", "")

YOUTUBE_BASE_URL = "https://www.googleapis.com/youtube/v3"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"