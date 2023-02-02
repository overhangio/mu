import os
import unittest

from mu import units
from mu.formats.olx import writer as w
from mu.formats.olx.reader import StringReader


class OlxReaderTests(unittest.TestCase):
    def test_chapter(self) -> None:
        reader = StringReader(
            """<chapter display_name='hello world'>
    <sequential display_name='My little sequential' />
</chapter>"""
        )
        chapter = list(reader.parse())[0]
        assert chapter is not None
        self.assertEqual("hello world", chapter.title)
        self.assertEqual("chapter", chapter.attributes["olx-type"])
        self.assertEqual("My little sequential", chapter.children[0].title)
        self.assertEqual("sequential", chapter.children[0].attributes["olx-type"])

    def test_video(self) -> None:
        reader = StringReader(
            "<video youtube_id_1_0='dQw4w9WgXcQ'><source src='myvideo.mp4'/></video>"
        )
        video = list(reader.parse())[0]
        assert isinstance(video, units.Video)
        self.assertEqual(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", video.sources[0]
        )
        self.assertEqual("myvideo.mp4", video.sources[1])

    def test_youtube_video_speed_ratio(self) -> None:
        reader = StringReader("<video youtube='1.00:dQw4w9WgXcQ'></video>")
        video = list(reader.parse())[0]
        assert isinstance(video, units.Video)
        self.assertEqual(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", video.sources[0]
        )

    def test_html(self) -> None:
        reader = StringReader("<html><p>hello world!</p></html>")
        html = list(reader.parse())[0]
        assert isinstance(html, units.RawHtml)
        self.assertEqual("<p>hello world!</p>", html.contents)


class OlxWriterTests(unittest.TestCase):
    def build_course(self, title: str = "") -> units.Course:
        return units.Course(
            attributes={
                "olx-org": "testorg",
                "olx-course": "testcourse",
                "olx-url_name": "testrun",
            },
            title=title,
        )

    def test_url_name_hash(self) -> None:
        course = self.build_course()
        unit1 = course.add_child(units.Unit())
        unit2 = course.add_child(units.Unit())
        unit3 = course.add_child(units.Unit(attributes={"olx-url_name": "someurl"}))
        unit4 = unit3.add_child(units.Unit())

        course_url_name = w.get_url_name_hash(course)
        unit1_url_name = w.get_url_name_hash(unit1)
        unit2_url_name = w.get_url_name_hash(unit2)
        unit3_url_name = w.get_url_name_hash(unit3)
        unit4_url_name = w.get_url_name_hash(unit4)

        self.assertEqual("", course_url_name)
        self.assertEqual("0", unit1_url_name)
        self.assertEqual("1", unit2_url_name)
        self.assertEqual("2", unit3_url_name)
        self.assertEqual("2_0", unit4_url_name)

    def test_url_name(self) -> None:
        course = self.build_course()
        unit1 = course.add_child(units.Unit())
        unit2 = course.add_child(units.Unit(attributes={"olx-url_name": "someurl"}))

        course_url_name = w.get_url_name(course)
        unit1_url_name1 = w.get_url_name(unit1)
        unit1_url_name2 = w.get_url_name(unit1)
        unit2_url_name = w.get_url_name(unit2)

        self.assertTrue(course_url_name)
        self.assertEqual(unit1_url_name1, unit1_url_name2)
        self.assertEqual("someurl", unit2_url_name)

    def test_course(self) -> None:
        course = self.build_course()
        writer = w.Writer()
        writer.write(course)
        self.assertEqual(2, len(writer.xml_paths))
        self.assertTrue(writer.xml_paths[0][0].attrs.get("url_name"))

    def test_video(self) -> None:
        video = units.Video(
            sources=["https://www.youtube.com/watch?v=dQw4w9WgXcQ", "myvideo.mp4"]
        )
        writer = w.Writer()
        writer.write(video)
        self.assertEqual(1, len(writer.xml_paths))
        video_xml = writer.xml_paths[0][0]
        self.assertEqual("dQw4w9WgXcQ", video_xml.attrs["youtube_id_1_0"])

    def test_video_with_title(self) -> None:
        course = self.build_course(title="course")
        chapter = course.add_child(units.Unit(title="chapter"))
        sequential = chapter.add_child(units.Unit(title="sequential"))
        vertical = sequential.add_child(units.Unit(title="vertical"))
        video_title = vertical.add_child(units.Unit(title="video"))
        _video = video_title.add_child(units.Video())
        writer = w.Writer()
        writer.write(course)
        self.assertEqual(6, len(writer.xml_paths))
        video_xml = writer.xml_paths[5][0]
        self.assertEqual("video", video_xml.attrs["display_name"])

    def test_raw_html(self) -> None:
        html = units.RawHtml(title="Hello", contents="<p>hello</p>")
        writer = w.Writer()
        writer.write(html)
        self.assertEqual("""<p>hello</p>""", str(writer.xml_paths[-1][0]))
        self.assertEqual(
            os.path.join("html", w.get_url_name(html) + ".html"),
            str(writer.xml_paths[-1][1]),
        )
