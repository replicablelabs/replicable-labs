from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LABS_ROOT = ROOT / "src" / "replicable" / "labs"


def _load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _write_env(path: Path, values: dict[str, str]) -> None:
    path.write_text("".join(f"{key}={value}\n" for key, value in values.items()))


def _langsmith_profile(environment: dict[str, str]) -> Path | None:
    path = Path(environment.get("LANGSMITH_CONFIG_FILE") or Path.home() / ".langsmith" / "config.json").expanduser().resolve()
    try:
        data = json.loads(path.read_text())
        name = environment.get("LANGSMITH_PROFILE") or data.get("current_profile") or "default"
        profile = data.get("profiles", {}).get(name, {})
        oauth = profile.get("oauth") or {}
        if profile.get("api_key") or oauth.get("access_token") or oauth.get("refresh_token"):
            return path
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return None


def _login_langsmith(values: dict[str, str], *, brewfile: Path) -> None:
    environment = {**os.environ, **values}
    if values.get("LANGSMITH_API_KEY", "").strip() or os.getenv("LANGSMITH_API_KEY", "").strip():
        return
    if _langsmith_profile(environment) is not None:
        print("Using your saved LangSmith login.")
        return

    print("Sign in to LangSmith to record and inspect this lab's traces.")
    method = input("LangSmith sign-in [browser/api-key] (browser): ").strip().lower() or "browser"
    if method == "api-key":
        secret = getpass.getpass("LANGSMITH_API_KEY (hidden): ").strip()
        if not secret:
            raise SystemExit("LangSmith login is required. Restart the lab to sign in.")
        values["LANGSMITH_API_KEY"] = secret
    elif method == "browser":
        if shutil.which("langsmith") is None:
            raise SystemExit(
                "LangSmith login is required. Install the exercise's host dependencies with "
                f"'brew bundle --file={brewfile}', then restart the lab to sign in."
            )
        status = subprocess.call(["langsmith", "auth", "login"], env=environment)
        if status != 0 or _langsmith_profile(environment) is None:
            raise SystemExit("LangSmith sign-in was not completed. Restart the lab to try again.")
    else:
        raise SystemExit("Choose browser or api-key for LangSmith sign-in.")


def _prompt_for_config(env_path: Path, *, require_langsmith: bool = False) -> None:
    values = _load_env(env_path)
    provider = values.get("MODEL_PROVIDER") or os.getenv("MODEL_PROVIDER")
    if provider not in {"openai", "anthropic"}:
        answer = input("Model provider [openai/anthropic] (openai): ").strip().lower()
        provider = answer or "openai"
    if provider not in {"openai", "anthropic"}:
        raise SystemExit("Provider must be openai or anthropic.")

    values["MODEL_PROVIDER"] = provider
    default_model = "gpt-4.1-mini" if provider == "openai" else "claude-3-5-haiku-latest"
    model = values.get("MODEL_NAME") or os.getenv("MODEL_NAME")
    values["MODEL_NAME"] = model or input(f"Model ({default_model}): ").strip() or default_model

    key_name = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    existing = values.get(key_name) or os.getenv(key_name)
    if not existing:
        print(f"No {key_name} found. Paste an API key, or press Enter to use an existing local/OIDC session.")
        secret = getpass.getpass(f"{key_name} (hidden): ").strip()
        if secret:
            values[key_name] = secret

    if require_langsmith:
        values["LANGSMITH_TRACING"] = "true"
        for key in ("LANGSMITH_PROFILE", "LANGSMITH_CONFIG_FILE", "LANGSMITH_ENDPOINT", "LANGSMITH_WORKSPACE_ID"):
            if not values.get(key, "").strip():
                values.pop(key, None)
        _login_langsmith(values, brewfile=env_path.with_name("Brewfile"))
        if not values.get("LANGSMITH_API_KEY", "").strip():
            # An empty example-file entry must not mask a key from the shell.
            values.pop("LANGSMITH_API_KEY", None)

    _write_env(env_path, values)
    print(f"Saved local lab configuration to {env_path}. It is ignored by git.")


def start_lab(uid: str) -> int:
    lab_dir = LABS_ROOT / uid
    compose_file = lab_dir / "docker-compose.yml"
    if not compose_file.exists():
        known = sorted(path.name for path in LABS_ROOT.iterdir() if path.is_dir()) if LABS_ROOT.exists() else []
        suffix = f" Available labs: {', '.join(known)}" if known else ""
        raise SystemExit(f"Unknown lab '{uid}'.{suffix}")
    if shutil.which("docker") is None:
        raise SystemExit("Docker is required. Install Docker Desktop and try again.")

    env_path = lab_dir / ".env"
    _prompt_for_config(env_path, require_langsmith=uid == "deep-agents-langgraph-101")
    command = ["docker", "compose", "-f", str(compose_file), "run", "--build", "--rm"]
    process_env = os.environ.copy()
    process_env.update(_load_env(env_path))
    profile = _langsmith_profile(process_env) if uid == "deep-agents-langgraph-101" else None
    if profile is not None:
        # Mount the directory so atomic OAuth token refreshes can be persisted.
        command.extend(["--volume", f"{profile.parent}:/run/langsmith-profile"])
        process_env["LANGSMITH_CONTAINER_CONFIG_FILE"] = f"/run/langsmith-profile/{profile.name}"
    command.append("demo")
    return subprocess.call(command, cwd=lab_dir, env=process_env)


def main() -> None:
    parser = argparse.ArgumentParser(prog="replicable")
    subparsers = parser.add_subparsers(dest="command", required=True)
    labs = subparsers.add_parser("labs", help="run Replicable labs")
    labs_subparsers = labs.add_subparsers(dest="labs_command", required=True)
    start = labs_subparsers.add_parser("start", help="start a lab locally")
    start.add_argument("demo_uid")
    args = parser.parse_args()
    if args.command == "labs" and args.labs_command == "start":
        raise SystemExit(start_lab(args.demo_uid))

