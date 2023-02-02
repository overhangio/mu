import unittest

from mu.utils import youtube


class UtilsTests(unittest.TestCase):
    def test_youtube_is_valid_url(self) -> None:
        self.assertTrue(youtube.is_video_url("https://www.youtube.com/watch?v=1234"))
        self.assertTrue(youtube.is_video_url("https://youtube.com/watch?v=1234"))
        self.assertTrue(youtube.is_video_url("https://youtube.com/watch?v=123_4"))
        self.assertTrue(youtube.is_video_url("http://youtube.com/watch?v=1234"))
        self.assertTrue(youtube.is_video_url("https://youtu.be/1234"))
        self.assertEqual("1234", youtube.get_video_id("https://youtu.be/1234"))
        # dash character is not supported
        self.assertFalse(youtube.is_video_url("https://youtube.com/watch?v=7-8"))
