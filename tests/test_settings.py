from pathlib import Path

from todomate_mcp.settings import RefreshTokenStore, load_auth_settings, load_environment


def test_local_dotenv_loads_refresh_token_without_password(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("TODOMATE_FIREBASE_API_KEY=key\nTODOMATE_REFRESH_TOKEN=stored\n")
    settings = load_auth_settings(dotenv, {})
    assert settings is not None
    assert (settings.api_key, settings.email, settings.password, settings.refresh_token) == ("key", None, None, "stored")


def test_environment_overrides_dotenv_and_store_rotates_token(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("# local secret\nTODOMATE_FIREBASE_API_KEY=old\nTODOMATE_REFRESH_TOKEN=old-token\n")
    store = RefreshTokenStore(dotenv)
    store.save("new-token")
    settings = load_auth_settings(dotenv, {"TODOMATE_FIREBASE_API_KEY": "new"})
    assert settings is not None and (settings.api_key, settings.refresh_token) == ("new", "new-token")
    assert oct(dotenv.stat().st_mode & 0o777) == "0o600"


def test_load_environment_reads_dotenv_and_environment_overrides(tmp_path: Path):
    dotenv = tmp_path / ".env"
    dotenv.write_text("TODOMATE_MCP_ACCESS_TOKEN=from-file\nTODOMATE_MCP_PORT=8000\n")

    assert load_environment(dotenv, {"TODOMATE_MCP_ACCESS_TOKEN": "from-env"}) == {
        "TODOMATE_MCP_ACCESS_TOKEN": "from-env",
        "TODOMATE_MCP_PORT": "8000",
    }
