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
        assert isinstance(chapter, units.Collection)
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

    def test_poll(self) -> None:
        reader = StringReader(
            """<poll answers='[
    [
        "answer1",
        {
            "img": "",
            "img_alt": "",
            "label": "Answer1"
        }
    ],
    [
        "answer2",
        {
            "img": "",
            "img_alt": "",
            "label": "Answer2"
        }
    ]
]' display_name="Poll" feedback="Feedback Text." max_submissions="10" private_results="true" question="Poll Question" xblock-family="xblock.v1"></poll>"""
        )
        poll = list(reader.parse())[0]
        assert isinstance(poll, units.Survey)
        self.assertListEqual(
            poll.answers,
            [
                ["answer1", {"img": "", "img_alt": "", "label": "Answer1"}],
                ["answer2", {"img": "", "img_alt": "", "label": "Answer2"}],
            ],
        )
        self.assertListEqual(poll.questions, ["Poll Question"])
        self.assertEqual(poll.feedback, "Feedback Text.")
        self.assertDictEqual(
            poll.attributes,
            {
                "display_name": "Poll",
                "max_submissions": "10",
                "private_results": "true",
                "xblock-family": "xblock.v1",
                "olx-type": "poll",
            },
        )

    def test_survey(self) -> None:
        reader = StringReader(
            """<survey answers='[
    [
        "answer1",
        "Answer1"
    ],
    [
        "answer2",
        "Answer2"
    ]
]' block_name="Survey" feedback="Feedback Text." max_submissions="10" private_results="true" questions='[
    [
        "question1",
        {
            "img": "",
            "img_alt": "",
            "label": "Question1"
        }
    ],
    [
        "question2",
        {
            "img": "",
            "img_alt": "",
            "label": "Question2"
        }
    ]
]' xblock-family="xblock.v1"></survey>"""
        )
        survey = list(reader.parse())[0]
        assert isinstance(survey, units.Survey)

        self.assertListEqual(
            survey.answers, [["answer1", "Answer1"], ["answer2", "Answer2"]]
        )
        self.assertListEqual(
            survey.questions,
            [
                ["question1", {"img": "", "img_alt": "", "label": "Question1"}],
                ["question2", {"img": "", "img_alt": "", "label": "Question2"}],
            ],
        )
        self.assertEqual(survey.feedback, "Feedback Text.")
        self.assertDictEqual(
            survey.attributes,
            {
                "block_name": "Survey",
                "max_submissions": "10",
                "private_results": "true",
                "xblock-family": "xblock.v1",
                "olx-type": "survey",
            },
        )


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
        unit3 = course.add_child(
            units.Collection(attributes={"olx-url_name": "someurl"})
        )
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
        chapter = course.add_child(units.Collection(title="chapter"))
        sequential = chapter.add_child(units.Collection(title="sequential"))
        vertical = sequential.add_child(units.Collection(title="vertical"))
        video_title = vertical.add_child(units.Collection(title="video"))
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

    def test_poll(self) -> None:
        survey = units.Survey(
            attributes={"private_results": "true", "max_submissions": "10"},
            title="Poll",
            answers=["Answer1", "Answer2", "Answer3"],
            questions=["Poll Question"],
            feedback="Feedback Text.",
        )
        writer = w.Writer()
        writer.write(survey)
        self.assertEqual(len(writer.unit_xml), 1)
        poll_tag = [v for v in writer.unit_xml.values()][0]
        poll_tag_attrs = poll_tag.attrs
        poll_tag_attrs.pop("url_name", "")
        self.assertDictEqual(
            {
                "display_name": "Poll",
                "private_results": "true",
                "max_submissions": "10",
                "xblock-family": "xblock.v1",
                "question": "Poll Question",
                "answers": '[\n    [\n        "answer1",\n        {\n            "img": "",\n            "img_alt": "",\n            "label": "Answer1"\n        }\n    ],\n    [\n        "answer2",\n        {\n            "img": "",\n            "img_alt": "",\n            "label": "Answer2"\n        }\n    ],\n    [\n        "answer3",\n        {\n            "img": "",\n            "img_alt": "",\n            "label": "Answer3"\n        }\n    ]\n]',
                "feedback": "Feedback Text.",
            },
            poll_tag_attrs,
        )

    def test_survey(self) -> None:
        survey = units.Survey(
            attributes={"private_results": "true", "max_submissions": "10"},
            title="Survey",
            answers=["Answer1", "Answer2"],
            questions=["Question1", "Question2"],
            feedback="Feedback Text.",
        )
        writer = w.Writer()
        writer.write(survey)
        self.assertEqual(len(writer.unit_xml), 1)
        survey_tag = [v for v in writer.unit_xml.values()][0]
        survey_tag_attrs = survey_tag.attrs
        survey_tag_attrs.pop("url_name", "")
        self.assertDictEqual(
            {
                "block_name": "Survey",
                "private_results": "true",
                "max_submissions": "10",
                "xblock-family": "xblock.v1",
                "questions": '[\n    [\n        "question1",\n        {\n            "img": "",\n            "img_alt": "",\n            "label": "Question1"\n        }\n    ],\n    [\n        "question2",\n        {\n            "img": "",\n            "img_alt": "",\n            "label": "Question2"\n        }\n    ]\n]',
                "answers": '[\n    [\n        "answer1",\n        "Answer1"\n    ],\n    [\n        "answer2",\n        "Answer2"\n    ]\n]',
                "feedback": "Feedback Text.",
            },
            survey_tag_attrs,
        )
