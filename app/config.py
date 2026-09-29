from pydantic_settings import BaseSettings, SettingsConfigDict

# OpenAI-compatible chat providers the AI representative can use (tools never call the LLM).
PROVIDERS = {
    "nim": {"base_url": "https://integrate.api.nvidia.com/v1", "model": "meta/llama-3.1-70b-instruct", "keys_env": "NIM_API_KEYS"},
    "groq": {"base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile", "keys_env": "GROQ_API_KEYS"},
    "xai": {"base_url": "https://api.x.ai/v1", "model": "grok-3", "keys_env": "XAI_API_KEYS"},
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    llm_provider: str = "nim"  # nim | groq | xai
    llm_model: str = ""  # overrides the provider's default model
    llm_base_url: str = ""  # overrides the provider's default URL
    nim_api_keys: str = ""
    groq_api_keys: str = ""
    xai_api_keys: str = ""
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "meta/llama-3.1-70b-instruct"
    tool_timeout_s: float = 20.0  # time limit for symbolic tools (solve, integrate, limits, series)

    @property
    def provider(self) -> str:
        p = self.llm_provider.strip().lower()
        if p not in PROVIDERS:
            raise ValueError(f"LLM_PROVIDER must be one of {', '.join(PROVIDERS)} (got {self.llm_provider!r})")
        return p

    @property
    def base_url(self) -> str:
        if self.llm_base_url:
            return self.llm_base_url
        return self.nim_base_url if self.provider == "nim" else PROVIDERS[self.provider]["base_url"]

    @property
    def model(self) -> str:
        if self.llm_model:
            return self.llm_model
        return self.nim_model if self.provider == "nim" else PROVIDERS[self.provider]["model"]

    @property
    def keys_env(self) -> str:
        return PROVIDERS[self.provider]["keys_env"]

    @property
    def key_list(self) -> list[str]:
        raw = {"nim": self.nim_api_keys, "groq": self.groq_api_keys, "xai": self.xai_api_keys}[self.provider]
        return [k.strip() for k in raw.split(",") if k.strip()]


settings = Settings()
