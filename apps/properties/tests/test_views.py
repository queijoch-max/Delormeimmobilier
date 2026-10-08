import shutil
import tempfile
from io import BytesIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.ai.testing import FakeLLM
from apps.properties.models import Property

from .factories import make_agent, make_property

TEMP_MEDIA = tempfile.mkdtemp()


def fake_image(name="photo.jpg") -> SimpleUploadedFile:
    buf = BytesIO()
    Image.new("RGB", (10, 10), "navy").save(buf, format="JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class PublicSiteTests(TestCase):
    def setUp(self):
        agent = make_agent()
        self.online = make_property(agent, title="En ligne", listing_text="Texte", is_published=True)
        self.draft = make_property(agent, title="Brouillon", listing_text="Texte", is_published=False)

    def test_home_lists_only_published(self):
        response = self.client.get(reverse("public:home"))
        self.assertContains(response, "En ligne")
        self.assertNotContains(response, "Brouillon")

    def test_filters(self):
        make_property(self.online.agent, title="Maison louée", kind="maison", transaction="location",
                      price=1200, neighborhood="Procé", listing_text="x", is_published=True)
        response = self.client.get(reverse("public:home"), {"transaction": "location"})
        self.assertContains(response, "Maison louée")
        self.assertNotContains(response, "En ligne")

    def test_detail_of_draft_is_404(self):
        self.assertEqual(self.client.get(self.online.get_absolute_url()).status_code, 200)
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class DashboardTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.agent = make_agent("claire")
        self.colleague = make_agent("julien")
        self.mine = make_property(self.agent, title="Mon bien")
        self.theirs = make_property(self.colleague, title="Bien du collègue")
        self.client.force_login(self.agent)

    def test_list_shows_only_my_properties(self):
        response = self.client.get(reverse("dashboard:home"))
        self.assertContains(response, "Mon bien")
        self.assertNotContains(response, "Bien du collègue")

    def test_cannot_touch_a_colleague_property(self):
        for name in ["dashboard:edit", "dashboard:listing", "dashboard:delete"]:
            with self.subTest(view=name):
                self.assertEqual(self.client.get(reverse(name, args=[self.theirs.pk])).status_code, 404)

    def test_create_property_with_photos(self):
        response = self.client.post(reverse("dashboard:create"), {
            "title": "Nouveau T2", "kind": "appartement", "transaction": "vente", "price": 200000,
            "surface": 45, "rooms": 2, "bedrooms": 1, "neighborhood": "Zola", "highlights": "", "notes": "",
            "new_photos": [fake_image("a.jpg"), fake_image("b.jpg")],
        })
        prop = Property.objects.get(title="Nouveau T2")
        self.assertRedirects(response, reverse("dashboard:listing", args=[prop.pk]))
        self.assertEqual(prop.agent, self.agent)
        self.assertEqual(prop.photos.count(), 2)

    def test_bedrooms_cannot_exceed_rooms(self):
        response = self.client.post(reverse("dashboard:create"), {
            "title": "Erreur", "kind": "appartement", "transaction": "vente", "price": 1,
            "surface": 10, "rooms": 1, "bedrooms": 3, "neighborhood": "Zola",
        })
        self.assertContains(response, "plus de chambres que de pièces")

    def test_generate_then_publish_listing(self):
        url = reverse("dashboard:listing", args=[self.mine.pk])
        with mock.patch("apps.properties.services.get_llm", return_value=FakeLLM("Texte IA")):
            self.client.post(url, {"action": "generate"})
        self.mine.refresh_from_db()
        self.assertEqual(self.mine.listing_text, "Texte IA")

        self.client.post(url, {"action": "publish", "listing_text": "Texte IA corrigé par Claire"})
        self.mine.refresh_from_db()
        self.assertTrue(self.mine.is_published)
        self.assertEqual(self.mine.listing_text, "Texte IA corrigé par Claire")

    def test_ai_failure_shows_message(self):
        from apps.ai import LLMError

        url = reverse("dashboard:listing", args=[self.mine.pk])
        with mock.patch("apps.properties.services.get_llm", return_value=FakeLLM(error=LLMError("IA en panne"))):
            response = self.client.post(url, {"action": "generate"}, follow=True)
        self.assertContains(response, "IA en panne")

    def test_delete_photo_of_colleague_is_404(self):
        photo = self.theirs.photos.create(image=fake_image())
        response = self.client.post(reverse("dashboard:photo_delete", args=[photo.pk]))
        self.assertEqual(response.status_code, 404)
