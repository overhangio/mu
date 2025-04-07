import unittest

from mu import units
from mu.formats.html.reader import DocumentReader, HtmlReader, StringReader
from mu.formats.html.reader import beautiful_soup as read_bs
from mu.formats.html.reader import get_header_level
from mu.formats.html.writer import UnstyledWriter, Writer


class HtmlReaderTests(unittest.TestCase):
    def test_header_level(self) -> None:
        self.assertEqual(1, get_header_level("h1"))
        self.assertEqual(2, get_header_level("h2"))
        self.assertEqual(3, get_header_level("h3"))
        self.assertIsNone(get_header_level("p"))
        self.assertIsNone(get_header_level("span"))
        self.assertIsNone(get_header_level("hspan"))

    def test_top_level_read(self) -> None:
        reader = DocumentReader(
            read_bs(
                """<!DOCTYPE html>
<html>
 <head>
 </head>
 <body>
  <h1 data-key1='val1'>
   Python programming 101
  </h1>
 </body>
</html>
"""
            )
        )
        course = reader.read()
        self.assertEqual("Python programming 101", course.title)
        self.assertEqual("val1", course.attributes["key1"])

    def test_read_with_children(self) -> None:
        reader = DocumentReader(
            read_bs(
                """<!DOCTYPE html>
<html>
 <head>
 </head>
 <body>
  <h1>title 1</h1>
  <h2>title 2.1</h2>
  <h2>title 2.2</h2>
  <h3>title 3</h3>
 </body>
</html>
"""
            )
        )
        course = reader.read()
        self.assertEqual("title 1", course.title)
        self.assertEqual(2, len(course.children))

        assert isinstance(course.children[0], units.Collection)
        self.assertEqual("title 2.1", course.children[0].title)
        self.assertEqual(0, len(course.children[0].children))

        assert isinstance(course.children[1], units.Collection)
        self.assertEqual("title 2.2", course.children[1].title)
        self.assertEqual(1, len(course.children[1].children))

        assert isinstance(course.children[1].children[0], units.Collection)
        self.assertEqual("title 3", course.children[1].children[0].title)
        self.assertEqual(0, len(course.children[1].children[0].children))

    def test_video(self) -> None:
        reader = StringReader(
            """
<h1>My amazing video course</h1>
<section data-mu-type="video">
    <h2>Video 1</h2>
    <video>
        <source src="https://youtu.be/dQw4w9WgXcQ">
        <source src="/media/cc0-videos/flower.mp4">
    </video>
</section>
"""
        )
        course = reader.read()
        video = course.children[0]
        self.assertEqual("Video 1", video.title)
        assert isinstance(video, units.Video)
        self.assertEqual(
            ["https://youtu.be/dQw4w9WgXcQ", "/media/cc0-videos/flower.mp4"],
            video.sources,
        )

    def test_survey(self) -> None:
        reader = StringReader(
            """
<h1>Survey</h1>
<section data-mu-type="survey">
   <h2 data-max_submissions="10" data-private_results="true" data-xblock-family="xblock.v1">
    My Survey
   </h2>
   <p>
    Question1
   </p>
   <p>
    Question2
   </p>
   <ul>
    <li>
     Answer1
    </li>
    <li>
     Answer2
    </li>
   </ul>
   <code>
    Feedback Text.
   </code>
  </section>
"""
        )
        course = reader.read()
        survey = course.children[0]
        self.assertEqual("My Survey", survey.title.strip(" \n"))
        assert isinstance(survey, units.Survey)
        self.assertListEqual(
            ["Answer1", "Answer2"],
            survey.answers,
        )

        self.assertListEqual(
            ["Question1", "Question2"],
            survey.questions,
        )
        self.assertEqual("Feedback Text.", survey.feedback)
        self.assertDictEqual(
            {
                "max_submissions": "10",
                "private_results": "true",
                "xblock-family": "xblock.v1",
            },
            survey.attributes,
        )

    def test_video_no_source(self) -> None:
        reader = StringReader(
            """
<h1>My amazing video course</h1>
<section data-mu-type="video">
    <h2>Video 1</h2>
    <video src="/media/cc0-videos/flower.mp4"></video>
</section>"""
        )
        course = reader.read()
        video = course.children[0]
        assert isinstance(video, units.Video)
        self.assertEqual(["/media/cc0-videos/flower.mp4"], video.sources)

    def test_video_duplicate_sources(self) -> None:
        reader = StringReader(
            """
<h1>My amazing video course</h1>
<section data-mu-type="video">
    <h2>Video 1</h2>
    <video src="/media/cc0-videos/flower.mp4">
        <source src="/media/cc0-videos/flower.mp4">
    </video>
</section>"""
        )
        course = reader.read()
        video = course.children[0]
        assert isinstance(video, units.Video)
        self.assertEqual(["/media/cc0-videos/flower.mp4"], video.sources)

    def test_youtube_iframe(self) -> None:
        reader = StringReader(
            """
<h1>My amazing youtube video course</h1>
<section data-mu-type="video">
    <iframe src='https://www.youtube.com/embed/dQw4w9WgXcQ'></iframe>
</section>
"""
        )
        course = reader.read()
        video = course.children[0]
        assert isinstance(video, units.Video)
        self.assertEqual(["https://www.youtube.com/watch?v=dQw4w9WgXcQ"], video.sources)

    def test_html_paragraphs(self) -> None:
        reader = StringReader(
            """
<h1>My html course</h1>
<p>Paragraph 1 <img src="https://www.google.com/images/logo.png"></p>
<p>Paragraph 2</p>
"""
        )
        course = reader.read()
        self.assertEqual(1, len(course.children))
        child = course.children[0]
        assert isinstance(child, units.RawHtml)
        self.assertEqual(
            """<p>Paragraph 1 <img src="https://www.google.com/images/logo.png"/></p>
<p>Paragraph 2</p>""",
            child.contents,
        )

    def test_unit_without_header(self) -> None:
        reader = HtmlReader(read_bs("<p>Paragraph</p>").p)
        parsed_units = list(reader.parse())
        self.assertEqual(1, len(parsed_units))
        assert isinstance(parsed_units[0], units.RawHtml)
        self.assertEqual("<p>Paragraph</p>", parsed_units[0].contents)

    def test_raw_html_data_attributes(self) -> None:
        reader = StringReader(
            """
<h1>My html course</h1>
<p data-attr1="val1" attr2="val2", data-attr3="val3">Paragraph</p>
"""
        )
        course = reader.read()
        self.assertEqual(1, len(course.children))
        child = course.children[0]
        assert isinstance(child, units.RawHtml)
        self.assertEqual(
            {
                "attr1": "val1",
                "attr3": "val3",
            },
            child.attributes,
        )

    def test_multi_raw_html_units(self) -> None:
        reader = StringReader(
            """
<h1>My html course</h1>
<p>Paragraph 1 <img src="https://www.google.com/images/logo.png"></p>
<p>Paragraph 2</p>
<video src="foo.mp4"></video>
<p>Paragraph 3</p>
"""
        )
        course = reader.read()
        self.assertEqual(1, len(course.children))
        child = course.children[0]
        assert isinstance(child, units.RawHtml)
        self.assertEqual(
            """<p>Paragraph 1 <img src="https://www.google.com/images/logo.png"/></p>
<p>Paragraph 2</p>
<video src="foo.mp4"></video>
<p>Paragraph 3</p>""",
            child.contents,
        )


class HtmlWriterTests(unittest.TestCase):
    def test_top_level_serialization(self) -> None:
        course = units.Course(title="Python programming 101")
        writer = UnstyledWriter()
        writer.write(course)
        output = writer.dumps()
        self.assertEqual(
            """<!DOCTYPE html>
<html>
 <head>
 </head>
 <body>
  <h1>
   Python programming 101
  </h1>
 </body>
</html>""",
            output,
        )

    def test_top_level_with_subunit_serialization(self) -> None:
        course = units.Course(title="Python programming 101")
        course.add_child(units.Course(title="Part1: variables"))
        writer = UnstyledWriter()
        writer.write(course)
        output = writer.dumps()
        self.assertEqual(
            """<!DOCTYPE html>
<html>
 <head>
 </head>
 <body>
  <h1>
   Python programming 101
  </h1>
  <h2>
   Part1: variables
  </h2>
 </body>
</html>""",
            output,
        )

    def test_video(self) -> None:
        writer = Writer()
        writer.write(
            units.Video(sources=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        )
        iframe = writer.document.find(name="iframe")
        self.assertEqual(
            "https://www.youtube.com/embed/dQw4w9WgXcQ", iframe.attrs["src"]
        )

    def test_survey(self) -> None:
        writer = Writer()
        writer.write(
            units.Survey(
                attributes={"private_results": "true", "max_submissions": "10"},
                title="My Survey",
                answers=["Answer1", "Answer2"],
                questions=["Question1", "Question2"],
                feedback="Feedback Text.",
            )
        )
        output = writer.dumps()
        self.assertEqual(
            """<!DOCTYPE html>
<html>
 <head>
 </head>
 <body>
  <section data-mu-type="survey">
   <h1 data-max_submissions="10" data-private_results="true" data-xblock-family="xblock.v1">
    My Survey
   </h1>
   <p>
    Question1
   </p>
   <p>
    Question2
   </p>
   <ul>
    <li>
     Answer1
    </li>
    <li>
     Answer2
    </li>
   </ul>
   <code>
    Feedback Text.
   </code>
  </section>
 </body>
</html>""",
            output,
        )

    def test_raw_html(self) -> None:
        writer = Writer()
        writer.write(units.RawHtml(contents="<p>hello</p>"))
        self.assertEqual("hello", writer.document.p.string)
