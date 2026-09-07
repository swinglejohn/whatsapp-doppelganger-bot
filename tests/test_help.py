import copy
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


class HelpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        old_cwd = os.getcwd()
        os.chdir(self.temp.name)
        self.addCleanup(os.chdir, old_cwd)
        self.completions = Mock()
        self.completions.create.side_effect = AssertionError("Unexpected AI call")
        # Replace the provider before importing the server, so these tests
        # cannot create a real OpenAI client or load production credentials.
        stubs = {
            "openai": types.SimpleNamespace(OpenAI=lambda **kw: types.SimpleNamespace(
                chat=types.SimpleNamespace(completions=self.completions))),
            "dotenv": types.SimpleNamespace(load_dotenv=lambda: None),
            "tiktoken": types.SimpleNamespace(get_encoding=lambda _: types.SimpleNamespace(
                encode=lambda _: [1])),
        }
        source = Path(__file__).resolve().parents[1] / "server.py"
        spec = importlib.util.spec_from_file_location("fambot_test_server", source)
        self.server = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, stubs), patch.dict(os.environ, {
            "OPENAI_MODEL_NAME1": "test-model-1", "OPENAI_MODEL_NAME2": "test-model-2",
            "OPENAI_MODEL_NAME3": "test-model-3",
        }):
            spec.loader.exec_module(self.server)
        self.server.APP.config["TESTING"] = True
        self.http = self.server.APP.test_client()

    def request(self, text, chat="test-chat"):
        return self.http.get("/chat", query_string={"q": text, "chat_id": chat})

    def test_all_help_aliases_without_history_or_ai_call(self):
        for name in ("John", "John Swingle"):
            for trigger in ("fambot", "@fambot", "FaMbOt"):
                for option in ("help", "--help", "-h", "HELP"):
                    with self.subTest(name=name, trigger=trigger, option=option):
                        response = self.request(f"{name}:  {trigger}\t{option}  ")
                        self.assertEqual(response.status_code, 200)
                        self.assertIn("*FamBot help*", response.text)
                        self.assertIn("fambot <model> <context> <messages>", response.text)
        self.assertEqual(self.server.CHAT_HISTORIES, {})
        self.assertEqual(self.server.CHAT_COOLDOWNS, {})
        self.completions.create.assert_not_called()

    def test_help_preserves_existing_history_and_cooldown(self):
        self.server.CHAT_HISTORIES["test-chat"] = ["John: hello"]
        self.server.CHAT_COOLDOWNS["test-chat"] = 17
        before = copy.deepcopy(self.server.CHAT_HISTORIES)
        self.request("John: fambot help")
        self.assertEqual(self.server.CHAT_HISTORIES, before)
        self.assertEqual(self.server.CHAT_COOLDOWNS["test-chat"], 17)

    def test_disabled_chat_stays_silent(self):
        self.server.DISABLED_CHATS.add("test-chat")
        self.assertEqual(self.request("John: fambot --help").text, "No Message")
        self.completions.create.assert_not_called()

    def test_ordinary_mentions_are_not_commands(self):
        for text in ("John: ask fambot help later", "John: fambot-help", "John: hello", "John: "):
            self.assertEqual(self.request(text).text, "No Message")
        self.completions.create.assert_not_called()

    def test_existing_generation_triggers(self):
        self.completions.create.side_effect = None
        self.completions.create.return_value = types.SimpleNamespace(choices=[
            types.SimpleNamespace(message=types.SimpleNamespace(content="Jane: prediction"))])
        for text, model, messages in (
            ("John: fambot", "test-model-3", 2),
            ("John Swingle: @fambot 2 0 3", "test-model-2", 3),
        ):
            response = self.request(text)
            self.assertIn("*From FamBot*", response.text)
            call = self.completions.create.call_args.kwargs
            self.assertEqual(call["model"], model)
            self.assertEqual(call["messages"][0]["content"], f"predict {messages} messages")
            self.assertNotIn("fambot", call["messages"][1]["content"])


if __name__ == "__main__":
    unittest.main()
