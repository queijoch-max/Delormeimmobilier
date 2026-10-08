from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.ai import LLMError
from apps.ai.testing import FakeLLM
from apps.properties import services
from apps.properties.models import Property

from .factories import make_agent, make_property


class PropertyModelTests(TestCase):
    def setUp(self):
        self.agent = make_agent("claire")

    def test_slug_is_unique(self):
        a = make_property(self.agent)
        b = make_property(self.agent)
        self.assertEqual(a.slug, "appartement-graslin-t3-avec-balcon")
        self.assertEqual(b.slug, "appartement-graslin-t3-avec-balcon-2")

    def test_highlights_list_ignores_bullets_and_blank_lines(self):
        prop = make_property(self.agent, highlights="- Balcon\n\n• Cave  \n")
        self.assertEqual(prop.highlights_list, ["Balcon", "Cave"])

    def test_published_requires_text(self):
        make_property(self.agent, title="Sans texte", is_published=True, listing_text="")
        visible = make_property(self.agent, title="Avec texte", is_published=True, listing_text="Annonce")
        self.assertQuerySetEqual(Property.objects.published(), [visible])

    def test_editable_by(self):
        other = make_agent("julien")
        boss = make_agent("marc", is_superuser=True)
        mine = make_property(self.agent)
        theirs = make_property(other)
        self.assertQuerySetEqual(Property.objects.editable_by(self.agent), [mine])
        self.assertEqual(set(Property.objects.editable_by(boss)), {mine, theirs})


class ListingServiceTests(TestCase):
    def setUp(self):
        self.prop = make_property(make_agent(), notes="DPE C", is_published=True, listing_text="Ancien texte")

    def test_generate_listing_sends_property_facts_and_saves_draft(self):
        llm = FakeLLM(reply="  Superbe T3 à Graslin.  ")
        text = services.generate_listing(self.prop, llm=llm)

        self.prop.refresh_from_db()
        self.assertEqual(text, "Superbe T3 à Graslin.")
        self.assertEqual(self.prop.listing_text, "Superbe T3 à Graslin.")
        self.assertIsNotNone(self.prop.listing_generated_at)
        self.assertFalse(self.prop.is_published, "un texte généré doit être relu avant publication")

        prompt = llm.last_call["messages"][-1].content
        for fact in ["Graslin", "70 m²", "300 000 €", "Balcon", "DPE C"]:
            self.assertIn(fact, prompt)
        self.assertIn("N'invente AUCUNE information", llm.last_call["system"])

    def test_generate_listing_error_keeps_existing_text(self):
        with self.assertRaises(LLMError):
            services.generate_listing(self.prop, llm=FakeLLM(error=LLMError("panne")))
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.listing_text, "Ancien texte")

    def test_publish_requires_text(self):
        self.prop.listing_text = " "
        with self.assertRaises(ValidationError):
            services.publish(self.prop)
