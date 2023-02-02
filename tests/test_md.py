import unittest

from mu import units
from mu.formats.md.reader import StringReader


class MarkdownTests(unittest.TestCase):
    def test_empty_course(self) -> None:
        course = StringReader("""# My Course""").read()
        self.assertEqual(0, len(course.children))
        self.assertEqual("My Course", course.title)

    def test_video(self) -> None:
        course = StringReader(
            """# My Course

::: {mu-type=video}

##### My Video

![](https://s3.amazonaws.com/edx-course-videos/edx-edx101/EDXSPCPJSP13-H010000_100.mp4)

:::
"""
        ).read()
        self.assertEqual(1, len(course.children))
        assert isinstance(course.children[0], units.Video)
        self.assertEqual("My Video", course.children[0].title)
