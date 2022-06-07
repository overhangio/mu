import unittest

from lecture import units


class UnitsTests(unittest.TestCase):
    def test_raw_html(self) -> None:
        raw1 = units.RawHtml(contents="  <p>Hello</p>\n  \n")
        raw2 = units.RawHtml(contents="<p>World!</p>\n")
        raw1.concatenate(raw2)
        self.assertEqual(
            """<p>Hello</p>
<p>World!</p>""",
            raw1.contents,
        )
