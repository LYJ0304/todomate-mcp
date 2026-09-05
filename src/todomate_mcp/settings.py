"""Local secret configuration and refresh-token persistence."""

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class AuthSettings:
    api_key: str
    email: str | None
    password: str | None
    refresh_token: str | None


def load_auth_settings(
    path: Path = Path(".env"), environ: Mapping[str, str] | None = None
) -> AuthSettings | None:
    values = load_environment(path, environ)
    api_key = values.get("TODOMATE_FIREBASE_API_KEY")
    refresh_token = values.get("TODOMATE_REFRESH_TOKEN")
    email, password = values.get("TODOMATE_EMAIL"), values.get("TODOMATE_PASSWORD")
    if not api_key or not (refresh_token or (email and password)):
        return None
    return AuthSettings(api_key, email, password, refresh_token)


def load_environment(path: Path = Path(".env"), environ: Mapping[str, str] | None = None) -> dict[str, str]:
    values = _read_dotenv(path)
    values.update({key: value for key, value in (environ or os.environ).items() if value})
    return values


class RefreshTokenStore:
    def __init__(self, path: Path = Path(".env")):
        self._path = path

    def save(self, token: str) -> None:
        if not token or "\n" in token or "\r" in token:
            raise ValueError("Invalid refresh token")
        lines = self._path.read_text().splitlines() if self._path.exists() else []
        setting = f"TODOMATE_REFRESH_TOKEN={token}"
        for index, line in enumerate(lines):
            if line.startswith("TODOMATE_REFRESH_TOKEN="):
                lines[index] = setting
                break
        else:
            lines.append(setting)
        temporary = self._path.with_name(f".{self._path.name}.tmp")
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, "w") as file:
            file.write("\n".join(lines) + "\n")
        os.replace(temporary, self._path)
        os.chmod(self._path, 0o600)


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for line in path.read_text().splitlines():
        key, separator, value = line.strip().partition("=")
        if separator and key and not key.startswith("#"):
            values[key] = value.strip().strip("\"'")
    return values
