import json

import httpx
from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings

from apps.ai import ChatTurn, LLMError, get_llm
from apps.ai.providers import DemoProvider, OpenAICompatibleProvider


def make_provider(handler) -> OpenAICompatibleProvider:
    """Fournisseur branché sur un faux serveur HTTP (aucun appel réseau réel)."""
    return OpenAICompatibleProvider(
        base_url="https://llm.test/v1", model="test-model", api_key="cle-test",
        transport=httpx.MockTransport(handler),
    )


class OpenAICompatibleProviderTests(SimpleTestCase):
    def test_sends_system_prompt_and_messages(self):
        seen = {}

        def handler(request: httpx.Request):
            seen["url"] = str(request.url)
            seen["auth"] = request.headers.get("Authorization")
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json={"choices": [{"message": {"content": "  Bonjour !  "}}]})

        text = make_provider(handler).complete(system="Consignes", messages=[ChatTurn("user", "Salut")])

        self.assertEqual(text, "Bonjour !")
        self.assertEqual(seen["url"], "https://llm.test/v1/chat/completions")
        self.assertEqual(seen["auth"], "Bearer cle-test")
        self.assertEqual(seen["body"]["model"], "test-model")
        self.assertEqual(
            seen["body"]["messages"],
            [{"role": "system", "content": "Consignes"}, {"role": "user", "content": "Salut"}],
        )

    def test_http_errors_become_llm_errors(self):
        for status, expected in [(429, "quota"), (401, "clé"), (500, "500")]:
            with self.subTest(status=status):
                provider = make_provider(lambda request, s=status: httpx.Response(s, json={}))
                with self.assertRaisesMessage(LLMError, expected):
                    provider.complete(system="s", messages=[ChatTurn("user", "q")])

    def test_network_error_becomes_llm_error(self):
        def handler(request):
            raise httpx.ConnectError("refusé")

        with self.assertRaises(LLMError):
            make_provider(handler).complete(system="s", messages=[ChatTurn("user", "q")])

    def test_malformed_or_empty_response(self):
        for body in [{"oops": True}, {"choices": [{"message": {"content": "   "}}]}]:
            with self.subTest(body=body):
                provider = make_provider(lambda request, b=body: httpx.Response(200, json=b))
                with self.assertRaises(LLMError):
                    provider.complete(system="s", messages=[ChatTurn("user", "q")])


class FactoryTests(SimpleTestCase):
    @override_settings(AI={"PROVIDER": "demo"})
    def test_demo(self):
        self.assertIsInstance(get_llm(), DemoProvider)

    @override_settings(AI={"PROVIDER": "ollama", "MODEL": "", "BASE_URL": "", "API_KEY": "", "TIMEOUT_SECONDS": 5})
    def test_ollama_defaults(self):
        llm = get_llm()
        self.assertEqual(llm.base_url, "http://localhost:11434/v1")
        self.assertEqual(llm.model, "qwen2.5:3b")

    @override_settings(AI={"PROVIDER": "groq", "MODEL": "", "BASE_URL": "", "API_KEY": "", "TIMEOUT_SECONDS": 5})
    def test_groq_requires_key(self):
        with self.assertRaises(ImproperlyConfigured):
            get_llm()

    @override_settings(AI={"PROVIDER": "inconnu"})
    def test_unknown_provider(self):
        with self.assertRaises(ImproperlyConfigured):
            get_llm()
