#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


CONFIG_PATH = Path("/usr/share/nginx/html/assets/config.json")


def bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def str_env(name: str, default: str) -> str:
    return os.getenv(name, default)


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    config["rest"] = {
        "ssl": bool_env("DSPACE_REST_SSL", False),
        "host": str_env("DSPACE_REST_HOST", "localhost"),
        "port": int_env("DSPACE_REST_PORT", 8080),
        "nameSpace": str_env("DSPACE_REST_NAMESPACE", "/server"),
        "baseUrl": str_env("DSPACE_REST_BASE_URL", "http://localhost:8080/server"),
    }
    config["ui"] = {
        "ssl": bool_env("DSPACE_UI_SSL", False),
        "host": str_env("DSPACE_UI_HOST", "localhost"),
        "port": int_env("DSPACE_UI_PORT", 4000),
        "nameSpace": str_env("DSPACE_UI_NAMESPACE", "/"),
        "baseUrl": str_env("DSPACE_UI_BASE_URL", "http://localhost:4000"),
    }
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.execvp("nginx", ["nginx", "-g", "daemon off;"])


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # pragma: no cover - container bootstrap path
        print(f"[dspace-frontend] failed to render config.json: {exc}", file=sys.stderr)
        raise
