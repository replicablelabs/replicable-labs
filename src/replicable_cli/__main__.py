from __future__ import annotations

import argparse
import getpass
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


def _prompt_for_config(env_path: Path) -> None:
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

    values.setdefault("LANGSMITH_TRACING", "false")
    if values.get("LANGSMITH_TRACING", "false").lower() == "true" and not (
        values.get("LANGSMITH_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    ):
        values["LANGSMITH_TRACING"] = "false"

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
    _prompt_for_config(env_path)
    command = ["docker", "compose", "-f", str(compose_file), "run", "--rm", "demo"]
    process_env = os.environ.copy()
    process_env.update(_load_env(env_path))
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


if __name__ == "__main__":
    main()

