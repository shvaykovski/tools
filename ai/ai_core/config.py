import os

# API Keys
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

# URLs
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8889")

# Defaults
DEFAULT_PROVIDER = "ollama"

# Per-provider default models (can be overridden by environment variables)
PROVIDER_MODELS = {
    "ollama": os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b"),
    "openai": os.getenv("OPENAI_MODEL", "gpt-4o"),
    "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
    "openrouter": os.getenv("OPENROUTER_MODEL", "google/gemini-flash-1.5"),
}

def get_default_model(provider):
    """Returns the default model for a given provider."""
    return PROVIDER_MODELS.get(provider, PROVIDER_MODELS["ollama"])
