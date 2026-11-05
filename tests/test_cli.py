import os
import json
from contextlib import ExitStack
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from replicable import cli


class RequiredLangSmithTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.lab = Path(self.directory.name) / "deep-agents-langgraph-101"
        self.lab.mkdir()
        (self.lab / "docker-compose.yml").touch()
        self.env_path = self.lab / ".env"
        self.env_path.write_text("LANGSMITH_TRACING=false\nLANGSMITH_API_KEY=\n")
        self.contexts = ExitStack()
        self.addCleanup(self.contexts.close)
        self.contexts.enter_context(patch.dict(os.environ, {
            "MODEL_PROVIDER": "openai",
            "MODEL_NAME": "test-model",
            "OPENAI_API_KEY": "test-provider-key",
            "LANGSMITH_CONFIG_FILE": str(self.lab / "login" / "config.json"),
        }, clear=True))
        self.contexts.enter_context(patch.object(cli, "LABS_ROOT", self.lab.parent))
        self.contexts.enter_context(patch.object(cli.shutil, "which", return_value="docker"))
        self.secret = self.contexts.enter_context(patch.object(cli.getpass, "getpass"))
        self.process = self.contexts.enter_context(patch.object(cli.subprocess, "call", return_value=0))
        self.contexts.enter_context(patch("builtins.print"))
        self.prompt = self.contexts.enter_context(patch("builtins.input", return_value="browser"))

    def test_missing_login_stops_before_docker_without_saving(self):
        before = self.env_path.read_text()
        self.secret.return_value = "  "
        self.prompt.return_value = "api-key"
        with self.assertRaisesRegex(SystemExit, "LangSmith login is required"):
            cli.start_lab(self.lab.name)
        self.process.assert_not_called()
        self.assertEqual(self.env_path.read_text(), before)

    def test_environment_key_enables_tracing_and_rebuilds_existing_image(self):
        os.environ["LANGSMITH_API_KEY"] = "test-langsmith-key"
        self.assertEqual(cli.start_lab(self.lab.name), 0)
        command = self.process.call_args.args[0]
        environment = self.process.call_args.kwargs["env"]
        self.assertIn("--build", command)
        self.assertEqual(environment["LANGSMITH_TRACING"], "true")
        self.assertEqual(environment["LANGSMITH_API_KEY"], "test-langsmith-key")

    def test_shell_key_survives_blank_saved_key_and_is_not_copied(self):
        os.environ["LANGSMITH_API_KEY"] = "test-shell-key"
        cli.start_lab(self.lab.name)
        self.secret.assert_not_called()
        environment = self.process.call_args.kwargs["env"]
        self.assertEqual(environment["LANGSMITH_API_KEY"], "test-shell-key")
        self.assertNotIn("test-shell-key", self.env_path.read_text())
        self.assertNotIn("LANGSMITH_API_KEY", cli._load_env(self.env_path))

    def test_saved_key_is_reused_and_disabled_tracing_is_migrated(self):
        self.env_path.write_text("LANGSMITH_TRACING=false\nLANGSMITH_API_KEY=test-saved-key\n")
        cli.start_lab(self.lab.name)
        self.secret.assert_not_called()
        environment = self.process.call_args.kwargs["env"]
        self.assertEqual(environment["LANGSMITH_API_KEY"], "test-saved-key")
        self.assertEqual(environment["LANGSMITH_TRACING"], "true")

    def test_workspace_and_endpoint_are_forwarded_from_shell(self):
        os.environ.update({
            "LANGSMITH_API_KEY": "test-shell-key",
            "LANGSMITH_ENDPOINT": "https://eu.api.smith.langchain.com",
            "LANGSMITH_WORKSPACE_ID": "test-workspace",
            "LANGSMITH_AGENT_ID": "test-agent",
        })
        cli.start_lab(self.lab.name)
        environment = self.process.call_args.kwargs["env"]
        self.assertEqual(environment["LANGSMITH_ENDPOINT"], os.environ["LANGSMITH_ENDPOINT"])
        self.assertEqual(environment["LANGSMITH_WORKSPACE_ID"], "test-workspace")
        self.assertEqual(environment["LANGSMITH_AGENT_ID"], "test-agent")


    def write_profile(self, data):
        path = Path(os.environ["LANGSMITH_CONFIG_FILE"])
        path.parent.mkdir()
        path.write_text(json.dumps(data))
        return path

    def test_oauth_login_starts_without_api_key_and_mounts_refresh_directory(self):
        path = self.write_profile({"current_profile": "dev", "profiles": {
            "dev": {"api_url": "https://eu.api.smith.langchain.com", "oauth": {
                "access_token": "test-access-token", "refresh_token": "test-refresh-token"
            }}
        }})
        cli.start_lab(self.lab.name)
        self.secret.assert_not_called()
        command = self.process.call_args.args[0]
        environment = self.process.call_args.kwargs["env"]
        self.assertIn(f"{path.resolve().parent}:/run/langsmith-profile", command)
        self.assertEqual(environment["LANGSMITH_CONTAINER_CONFIG_FILE"], "/run/langsmith-profile/config.json")
        self.assertNotIn("LANGSMITH_API_KEY", environment)
        self.assertNotIn("LANGSMITH_ENDPOINT", environment)
        self.assertNotIn("test-access-token", self.env_path.read_text())
        self.assertNotIn("test-refresh-token", self.env_path.read_text())

    def test_selected_profile_must_have_credentials(self):
        self.write_profile({"current_profile": "dev", "profiles": {
            "dev": {"oauth": {"access_token": "test-token"}}, "empty": {}
        }})
        os.environ["LANGSMITH_PROFILE"] = "empty"
        with self.assertRaisesRegex(SystemExit, "LangSmith sign-in was not completed"):
            cli.start_lab(self.lab.name)
        self.process.assert_called_once()
        self.assertEqual(self.process.call_args.args[0], ["langsmith", "auth", "login"])

    def test_invalid_profile_reports_login_instructions(self):
        path = Path(os.environ["LANGSMITH_CONFIG_FILE"])
        path.parent.mkdir()
        path.write_text("not valid JSON")
        with self.assertRaisesRegex(SystemExit, "LangSmith sign-in was not completed"):
            cli.start_lab(self.lab.name)
        self.process.assert_called_once()
        self.assertEqual(self.process.call_args.args[0], ["langsmith", "auth", "login"])


    def test_browser_login_completes_before_container_starts(self):
        def run(command, **kwargs):
            if command == ["langsmith", "auth", "login"]:
                self.write_profile({"current_profile": "dev", "profiles": {
                    "dev": {"oauth": {"access_token": "test-new-login"}}
                }})
            return 0
        self.process.side_effect = run
        cli.start_lab(self.lab.name)
        self.assertEqual(self.process.call_args_list[0].args[0], ["langsmith", "auth", "login"])
        self.assertEqual(self.process.call_count, 2)
        self.assertIn("--volume", self.process.call_args.args[0])
        self.assertEqual(self.process.call_args.kwargs["env"]["LANGSMITH_TRACING"], "true")
        self.secret.assert_not_called()

    def test_cancelled_browser_login_never_starts_docker(self):
        self.process.return_value = 1
        with self.assertRaisesRegex(SystemExit, "sign-in was not completed"):
            cli.start_lab(self.lab.name)
        self.process.assert_called_once()
        self.assertEqual(self.process.call_args.args[0], ["langsmith", "auth", "login"])

    def test_api_key_sign_in_is_hidden_and_starts_container(self):
        self.prompt.return_value = "api-key"
        self.secret.return_value = "test-prompted-key"
        cli.start_lab(self.lab.name)
        self.secret.assert_called_once_with("LANGSMITH_API_KEY (hidden): ")
        self.assertEqual(self.process.call_args.kwargs["env"]["LANGSMITH_API_KEY"], "test-prompted-key")
        self.assertEqual(self.process.call_count, 1)

    def test_missing_cli_explains_exercise_dependency_install(self):
        with patch.object(cli.shutil, "which", side_effect=lambda name: "docker" if name == "docker" else None):
            with self.assertRaisesRegex(SystemExit, "brew bundle --file="):
                cli.start_lab(self.lab.name)
        self.process.assert_not_called()


    def test_empty_provider_key_stops_before_login_or_docker(self):
        os.environ.pop("OPENAI_API_KEY")
        self.secret.return_value = "  "
        before = self.env_path.read_text()
        with self.assertRaisesRegex(SystemExit, "OPENAI_API_KEY is required"):
            cli.start_lab(self.lab.name)
        self.process.assert_not_called()
        self.prompt.assert_not_called()
        self.assertEqual(self.env_path.read_text(), before)

    def test_hidden_provider_key_is_forwarded_to_container(self):
        os.environ.pop("OPENAI_API_KEY")
        os.environ["LANGSMITH_API_KEY"] = "test-tracing-key"
        self.secret.return_value = "test-entered-provider-key"
        cli.start_lab(self.lab.name)
        self.secret.assert_called_once_with("OPENAI_API_KEY (hidden): ")
        self.assertEqual(self.process.call_args.kwargs["env"]["OPENAI_API_KEY"], "test-entered-provider-key")

    def test_blank_saved_provider_key_does_not_mask_shell_key(self):
        os.environ["LANGSMITH_API_KEY"] = "test-tracing-key"
        self.env_path.write_text("OPENAI_API_KEY=\n")
        cli.start_lab(self.lab.name)
        self.secret.assert_not_called()
        self.assertEqual(self.process.call_args.kwargs["env"]["OPENAI_API_KEY"], "test-provider-key")
        self.assertNotIn("OPENAI_API_KEY", cli._load_env(self.env_path))

    def test_anthropic_also_requires_its_provider_key(self):
        os.environ["MODEL_PROVIDER"] = "anthropic"
        self.secret.return_value = ""
        with self.assertRaisesRegex(SystemExit, "ANTHROPIC_API_KEY is required"):
            cli.start_lab(self.lab.name)
        self.secret.assert_called_once_with("ANTHROPIC_API_KEY (hidden): ")
        self.process.assert_not_called()


if __name__ == "__main__":
    unittest.main()
