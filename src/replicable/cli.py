from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
from pathlib import Path

from .openai_oauth import ChatGPTSession, SignInError

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
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
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


def _prompt_for_config(env_path: Path, *, require_langsmith: bool = False, auth_mode=None, reconnect=False) -> None:
    values = _load_env(env_path)
    provider = values.get("MODEL_PROVIDER") or os.getenv("MODEL_PROVIDER")
    if provider not in {"openai", "anthropic"}:
        answer = input("Model provider [openai/anthropic] (openai): ").strip().lower()
        provider = answer or "openai"
    if provider not in {"openai", "anthropic"}:
        raise SystemExit("Provider must be openai or anthropic.")

    values["MODEL_PROVIDER"] = provider
    if provider != "openai" and auth_mode == "browser":
        raise SystemExit("Browser sign-in is available for OpenAI. Select openai or use api-key for Anthropic.")
    key_name = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
    existing = values.get(key_name, "").strip() or os.getenv(key_name, "").strip()
    mode = "api-key"
    if provider == "openai":
        mode = auth_mode or os.getenv("OPENAI_AUTH_MODE") or values.get("OPENAI_AUTH_MODE")
        if not mode:
            mode = "api-key" if existing else input("OpenAI authentication [browser/api-key] (browser): ").strip().lower() or "browser"
        if mode not in {"browser", "api-key"}:
            raise SystemExit("Choose browser or api-key for OpenAI authentication.")
        values["OPENAI_AUTH_MODE"] = mode

    if mode == "browser":
        session = ChatGPTSession(env_path.parent / ".data" / "openai" / "session.json")
        try:
            if reconnect or not session.connected():
                session.sign_in()
            else:
                print("Using your saved ChatGPT login.")
            models = session.models()
        except SignInError as error:
            raise SystemExit(str(error)) from None
        slugs = [item["slug"] for item in models]
        model = os.getenv("MODEL_NAME") or values.get("MODEL_NAME")
        if model not in slugs:
            print("Models available to your ChatGPT account:")
            for index, item in enumerate(models, 1):
                print(f"  {index}. {item['display_name']} ({item['slug']})")
            answer = input("Model number or name (1): ").strip() or "1"
            model = slugs[int(answer) - 1] if answer.isdigit() and 1 <= int(answer) <= len(slugs) else answer
            if model not in slugs:
                raise SystemExit("Choose a model from your ChatGPT account's list.")
        values["MODEL_NAME"] = model
    elif not existing:
        print(f"This lab needs a {provider} API key for model calls. Your LangSmith login is separate.")
        if provider == "openai":
            print("Create an OpenAI API key at https://platform.openai.com/api-keys.")
        secret = getpass.getpass(f"{key_name} (hidden): ").strip()
        if not secret:
            raise SystemExit(f"{key_name} is required. Restart the lab and enter your provider API key at the hidden prompt.")
        values[key_name] = secret
    elif not values.get(key_name, "").strip():
        # Keep shell-provided keys out of .env, and do not mask them with blanks.
        values.pop(key_name, None)

    if mode == "api-key":
        default_model = "gpt-4.1-mini" if provider == "openai" else "claude-3-5-haiku-latest"
        model = values.get("MODEL_NAME") or os.getenv("MODEL_NAME")
        values["MODEL_NAME"] = model or input(f"Model ({default_model}): ").strip() or default_model

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


PLUGIN_CACHE = ROOT / ".data" / "plugins"


def _is_plugin(path: Path) -> bool:
    return (path / ".claude-plugin" / "plugin.json").exists()


def _plugin_dir(spec: dict) -> Path:
    """The plugin a host lab loads: a local checkout from REPLICABLE_HARNESS_DIR, or a clone at the pinned tag."""
    override = os.environ.get("REPLICABLE_HARNESS_DIR")
    if override:
        path = Path(override).expanduser().resolve()
        if not _is_plugin(path):
            raise SystemExit(f"REPLICABLE_HARNESS_DIR={override} is not a Claude Code plugin (no .claude-plugin/plugin.json).")
        return path
    target = PLUGIN_CACHE / f"{spec['name']}-{spec['ref']}"
    if not _is_plugin(target):
        if shutil.which("git") is None:
            raise SystemExit("This lab needs git to fetch its Claude Code plugin.")
        target.parent.mkdir(parents=True, exist_ok=True)
        print(f"Fetching {spec['name']} {spec['ref']} into {target.relative_to(ROOT)} ...")
        result = subprocess.run(["git", "-c", "advice.detachedHead=false", "clone", "--quiet", "--depth", "1",
                                 "--branch", spec["ref"],
                                 spec["repository"], str(target)])
        if result.returncode != 0 or not _is_plugin(target):
            raise SystemExit(f"Could not fetch {spec['repository']} at {spec['ref']}.")
    return target


def start_host_lab(lab_dir: Path, extra_args=()) -> int:
    """Run a lab that loads a Claude Code plugin, directly on this machine (no Docker)."""
    spec = json.loads((lab_dir / "lab.json").read_text())["plugin"]
    if shutil.which("claude") is None:
        raise SystemExit("This lab needs the Claude Code CLI. Install it from https://docs.claude.com/claude-code and run `claude` once to sign in.")
    plugin = _plugin_dir(spec)
    return subprocess.call(["claude", "--plugin-dir", str(plugin), *extra_args], cwd=ROOT)


def _is_host_lab(lab_dir: Path) -> bool:
    try:
        return json.loads((lab_dir / "lab.json").read_text()).get("kind") == "claude-code-plugin"
    except (OSError, ValueError, AttributeError):
        return False


def start_lab(uid: str, *, auth_mode=None, reconnect=False, extra_args=()) -> int:
    lab_dir = LABS_ROOT / uid
    compose_file = lab_dir / "docker-compose.yml"
    if not compose_file.exists() and _is_host_lab(lab_dir):
        return start_host_lab(lab_dir, extra_args)
    if not compose_file.exists():
        known = sorted(path.name for path in LABS_ROOT.iterdir() if path.is_dir()) if LABS_ROOT.exists() else []
        suffix = f" Available labs: {', '.join(known)}" if known else ""
        raise SystemExit(f"Unknown lab '{uid}'.{suffix}")
    if shutil.which("docker") is None:
        raise SystemExit("Docker is required. Install Docker Desktop and try again.")

    env_path = lab_dir / ".env"
    _prompt_for_config(env_path, require_langsmith=uid == "deep-agents-langgraph-101", auth_mode=auth_mode, reconnect=reconnect)
    command = ["docker", "compose", "-f", str(compose_file), "run", "--build", "--rm"]
    process_env = os.environ.copy()
    process_env.update(_load_env(env_path))
    if process_env.get("MODEL_PROVIDER") == "openai" and process_env.get("OPENAI_AUTH_MODE") == "browser":
        auth_dir = (lab_dir / ".data" / "openai").resolve()
        command.extend(["--volume", f"{auth_dir}:/run/openai-auth"])
        # Browser mode always uses its own session, even when a shell key exists.
        process_env["OPENAI_API_KEY"] = ""
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
    start.add_argument("--auth", choices=("browser", "api-key"), help="choose model authentication (browser uses ChatGPT)")
    start.add_argument("--login", action="store_true", help="sign in with ChatGPT again while retaining this lab's registration")
    start.add_argument("claude_args", nargs=argparse.REMAINDER, help="for Claude Code labs: extra arguments after -- are passed to claude")
    args = parser.parse_args()
    if args.command == "labs" and args.labs_command == "start":
        extra = [a for a in args.claude_args if a != "--"] if args.claude_args else []
        raise SystemExit(start_lab(args.demo_uid, auth_mode=args.auth, reconnect=args.login, extra_args=extra))

