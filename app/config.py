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

    # Web app platform (accounts, history, space company)
    secret_key: str = ""  # signs sessions and flight states; generated and kept next to the database if empty
    database_path: str = "data/reality.db"
    cookie_secure: bool = False  # set true behind HTTPS
    session_days: int = 30
    public_base_url: str = ""  # e.g. https://reality.plazmonix.ai (links in emails, Google sign-in callback)
    beta_invite_codes: str = ""  # comma separated; when set, sign-up needs one of them
    admin_emails: str = ""  # comma separated; these accounts see the admin page (sign-ups, feedback, usage)
    waitlist_origins: str = ""  # comma separated sites allowed to post to /api/waitlist, e.g. https://realityasm.com
    test_gate_username: str = ""  # when both are set, the whole app asks for this username and password (private testing)
    test_gate_password: str = ""
    owner_email: str = ""  # with OWNER_PASSWORD: this account is created on startup if missing, so no sign-up is needed
    owner_password: str = ""
    contact_email: str = "support@plazmonix.ai"
    enable_api_docs: bool = False  # /docs and /openapi.json stay off in production
    google_client_id: str = ""
    google_client_secret: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    simulate_rate_per_s: float = 25.0  # engine calls per user per second (burst of 4 s)
    ask_rate_per_min: float = 12.0

    @property
    def waitlist_origin_set(self) -> set[str]:
        return {o.strip().rstrip("/") for o in self.waitlist_origins.split(",") if o.strip()}

    @property
    def admins(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}

    @property
    def invite_codes(self) -> set[str]:
        return {c.strip() for c in self.beta_invite_codes.split(",") if c.strip()}

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
