from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    nim_api_keys: str = ""
    nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nim_model: str = "meta/llama-3.1-70b-instruct"
    tool_timeout_s: float = 20.0  # time limit for symbolic tools (solve, integrate, limits, series)

    @property
    def key_list(self) -> list[str]:
        return [k.strip() for k in self.nim_api_keys.split(",") if k.strip()]


settings = Settings()
