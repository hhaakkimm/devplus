from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Read from environment variables only (no env_file: make exports .env)."""

    database_url: str
    github_client_id: str
    github_client_secret: str
    allowed_github_logins: str = ""
    app_origin: str
    cookie_secure: bool = True
