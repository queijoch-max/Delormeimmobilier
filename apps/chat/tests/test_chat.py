import json
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.ai import LLMError
from apps.ai.testing import FakeLLM
from apps.chat import services
from apps.chat.models import ChatMessage
from apps.chat.prompts import OUT_OF_SCOPE_MARKER
from apps.properties.tests.factories import make_agent, make_property


class ChatServiceTests(TestCase):
    def setUp(self):
        self.agent = make_agent("claire", phone="06 11 22 33 44")
        self.online = make_property(self.agent, title="T3 Graslin", listing_text="Bel appartement.", is_published=True)
        self.draft = make_property(self.agent, title="Brouillon secret", listing_text="x", is_published=False)

    def ask(self, question, llm, current=None, session="s1"):
        return services.answer_question(question=question, session_key=session, current=current, llm=llm)

    def test_context_contains_only_published_properties(self):
        llm = FakeLLM("Oui, il y a un balcon.")
        self.ask("Y a-t-il un balcon ?", llm)
        system = llm.last_call["system"]
        self.assertIn("T3 Graslin", system)
        self.assertIn("06 11 22 33 44", system)
        self.assertNotIn("Brouillon secret", system)

    def test_answer_is_logged(self):
        result = self.ask("Y a-t-il un balcon ?", FakeLLM("Oui."), current=self.online)
        msg = ChatMessage.objects.get()
        self.assertEqual((msg.question, msg.answer, msg.property), ("Y a-t-il un balcon ?", "Oui.", self.online))
        self.assertEqual(result.status, ChatMessage.Status.ANSWERED)

    def test_out_of_scope_marker_is_detected_and_removed(self):
        result = self.ask("Écris-moi un poème", FakeLLM(f"{OUT_OF_SCOPE_MARKER} Je ne peux pas vous aider."))
        self.assertEqual(result.status, ChatMessage.Status.OUT_OF_SCOPE)
        self.assertEqual(result.text, "Je ne peux pas vous aider.")

    def test_guard_blocks_off_topic_question_before_answering(self):
        llm = FakeLLM(replies=["NON"])
        result = self.ask("Écris-moi un poème sur les chats", llm)
        self.assertEqual(len(llm.calls), 1, "le modèle ne doit pas être interrogé pour répondre")
        self.assertIn("Message du visiteur", llm.last_call["messages"][0].content)
        self.assertEqual((result.status, result.text), (ChatMessage.Status.OUT_OF_SCOPE, services.DEFAULT_REFUSAL))
        self.assertEqual(ChatMessage.objects.get().status, ChatMessage.Status.OUT_OF_SCOPE)

    def test_guard_lets_on_topic_question_through(self):
        llm = FakeLLM(replies=["OUI", "Oui, au 3e étage avec ascenseur."])
        result = self.ask("Il y a un ascenseur ?", llm, current=self.online)
        self.assertEqual(len(llm.calls), 2)
        self.assertEqual(result.text, "Oui, au 3e étage avec ascenseur.")

    def test_marker_alone_gets_default_refusal(self):
        result = self.ask("Météo ?", FakeLLM(OUT_OF_SCOPE_MARKER))
        self.assertEqual(result.text, services.DEFAULT_REFUSAL)

    def test_history_is_sent_to_the_model(self):
        self.ask("Quel est le prix ?", FakeLLM("300 000 €."), current=self.online)
        llm = FakeLLM("Oui.")
        self.ask("Et il est négociable ?", llm, current=self.online)
        roles = [(t.role, t.content) for t in llm.last_call["messages"]]
        self.assertEqual(roles, [
            ("user", "Quel est le prix ?"), ("assistant", "300 000 €."), ("user", "Et il est négociable ?"),
        ])

    def test_history_is_per_visitor(self):
        self.ask("Question du visiteur 1", FakeLLM("R1"), session="s1")
        llm = FakeLLM("R2")
        self.ask("Question du visiteur 2", llm, session="s2")
        self.assertEqual(len(llm.last_call["messages"]), 1)

    def test_llm_error_returns_fallback_and_logs_error(self):
        result = self.ask("Bonjour", FakeLLM(error=LLMError("panne")))
        self.assertFalse(result.ok)
        self.assertIn("02 40 00 00 00", result.text)
        self.assertEqual(ChatMessage.objects.get().status, ChatMessage.Status.ERROR)


class ChatApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.prop = make_property(make_agent(), listing_text="Texte", is_published=True)
        self.url = reverse("chat:ask")

    def post(self, payload):
        return self.client.post(self.url, json.dumps(payload), content_type="application/json")

    @mock.patch("apps.chat.services.get_llm", return_value=FakeLLM("Oui, il y a une cave."))
    def test_ask(self, _):
        response = self.post({"question": "Y a-t-il une cave ?", "property_id": self.prop.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"answer": "Oui, il y a une cave.", "status": "answered"})
        self.assertEqual(ChatMessage.objects.get().property, self.prop)

    def test_validation(self):
        self.assertEqual(self.post({"question": "  "}).status_code, 400)
        self.assertEqual(self.post({"question": "x" * 501}).status_code, 400)
        bad = self.client.post(self.url, "pas du json", content_type="application/json")
        self.assertEqual(bad.status_code, 400)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    @override_settings(CHAT_RATE_LIMIT=(2, 60))
    @mock.patch("apps.chat.services.get_llm", return_value=FakeLLM("ok"))
    def test_rate_limit(self, _):
        codes = [self.post({"question": f"q{i}"}).status_code for i in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    @mock.patch("apps.chat.services.get_llm", return_value=FakeLLM(error=LLMError("panne")))
    def test_ai_down_returns_503_with_friendly_message(self, _):
        response = self.post({"question": "Bonjour"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("agence", response.json()["answer"])


class ChatHistoryViewTests(TestCase):
    def test_agent_sees_own_and_general_questions_only(self):
        claire, julien = make_agent("claire"), make_agent("julien")
        mine = make_property(claire, title="Bien de Claire")
        theirs = make_property(julien, title="Bien de Julien")
        ChatMessage.objects.create(session_key="a", property=mine, question="Question sur mon bien", answer="r")
        ChatMessage.objects.create(session_key="b", property=theirs, question="Question chez Julien", answer="r")
        ChatMessage.objects.create(session_key="c", property=None, question="Question générale", answer="r")

        self.client.force_login(claire)
        response = self.client.get(reverse("chat:history"))
        self.assertContains(response, "Question sur mon bien")
        self.assertContains(response, "Question générale")
        self.assertNotContains(response, "Question chez Julien")
