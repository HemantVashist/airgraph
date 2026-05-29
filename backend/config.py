import os
from pydantic_settings import BaseSettings

# Resolve absolute path to .env dynamically relative to config.py location
# This ensures pydantic-settings always loads the .env file successfully
# regardless of what working directory uvicorn is started from.
current_dir = os.path.dirname(os.path.abspath(__file__))
env_file_path = os.path.abspath(os.path.join(current_dir, "..", ".env"))


class Settings(BaseSettings):
    llm_provider: str = "gemini"  # "gemini" or "openai"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    neo4j_uri: str
    neo4j_username: str
    neo4j_password: str

    class Config:
        env_file = env_file_path
        extra = "ignore"  # Ignore extra keys in .env (like TMDB_API_KEY) without crashing


settings = Settings()
