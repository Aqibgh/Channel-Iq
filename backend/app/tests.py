from django.test import SimpleTestCase

from .views import extract_video_id, extract_youtube_id, sanitize_filename


class ViewHelperTests(SimpleTestCase):
    """Protect the pure helpers exposed through the views compatibility facade."""

    def test_extract_video_id_supports_standard_and_short_youtube_urls(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=abc123"),
            "abc123",
        )
        self.assertEqual(
            extract_video_id("https://youtu.be/abc123"),
            "abc123",
        )

    def test_extract_youtube_id_requires_an_eleven_character_id(self):
        self.assertEqual(
            extract_youtube_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )
        self.assertIsNone(extract_youtube_id("https://example.com/video"))

    def test_sanitize_filename_removes_windows_reserved_characters(self):
        self.assertEqual(sanitize_filename('clip:final*?.mp4'), "clipfinal.mp4")
