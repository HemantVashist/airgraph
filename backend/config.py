from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    llm_provider: str = "gemini"  # "gemini" or "openai"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str
    tmdb_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
