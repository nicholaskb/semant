from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Build an absolute path to the .env file from this file's location.
# This makes it robust to wherever the script is run from.
env_path = Path(__file__).resolve().parent.parent / '.env'

class Settings(BaseSettings):
    """
    Centralized application settings.
    Settings are automatically loaded from the .env file found at the project root.
    """
    model_config = SettingsConfigDict(env_file=env_path, env_file_encoding='utf-8', extra='ignore')

    # GCS Bucket for Midjourney uploads
    GCS_BUCKET_NAME: str

    # Optional: Remote Knowledge Graph (SPARQL) configuration
    KG_REMOTE_ENABLED: bool = False
    KG_SPARQL_QUERY_ENDPOINT: str | None = None
    KG_SPARQL_UPDATE_ENDPOINT: str | None = None
    KG_VERIFY_SSL: bool = True


# Create a single, importable instance of the settings.
# This will raise a validation error if GCS_BUCKET_NAME is not found.
settings = Settings()

# Add a debug print to confirm the loaded value upon successful import.
print(f"--- SETTINGS LOADED SUCCESSFULLY ---")
print(f"GCS_BUCKET_NAME = {settings.GCS_BUCKET_NAME}")
print(f"KG_REMOTE_ENABLED = {settings.KG_REMOTE_ENABLED}")
print(f"KG_SPARQL_QUERY_ENDPOINT = {settings.KG_SPARQL_QUERY_ENDPOINT}")
print(f"KG_SPARQL_UPDATE_ENDPOINT = {settings.KG_SPARQL_UPDATE_ENDPOINT}")
print(f"------------------------------------")
