# Lecture: the course authoring tool for humans

Lecture is a tool for writing online courses in a human-friendly format and converting them to formats that can be understood by common learning management systems ([LMS](https://en.wikipedia.org/wiki/Learning_management_system)). In particular, Lecture can convert courses from Markdown to Open edX Learning XML ([OLX](https://edx.readthedocs.io/projects/edx-open-learning-xml/)).

⚠ This work is still in the alpha stage! Do not report issues just yet. ⚠

Supported formats:

- [Markdown](https://daringfireball.net/projects/markdown/): with [Pandoc-flavoured](https://garrettgman.github.io/rmarkdown/authoring_pandoc_markdown.html) header attributes.
- HTML 5
- Open Learning XML ([OLX](https://edx.readthedocs.io/projects/edx-open-learning-xml/) from [Open edX](https://openedx.org).

## Installation

    pip install git+https://github.com/overhangio/lecture

## Requirements

Conversion from and to Markdown is handled by Lecture with the help of [Pandoc](https://pandoc.org/). Thus, a recent version of Pandoc is required when working with Markdown documents. See the corresponding [installation instructions](https://pandoc.org/installing.html).

## Usage

    # Markdown -> OLX
    lecture /path/to/course.md /path/to/olx/
    # OLX -> HTML
    lecture /path/to/olx/course/ /path/to/course.html
    # HTML -> OLX
    lecture /path/to/course.html /path/to/olx/course/
    ...

When writing Markdown files, the generated documents will include non-standard (but widely recognized) [header identifiers](https://garrettgman.github.io/rmarkdown/authoring_pandoc_markdown.html#header-identifiers) to store the course unit attributes.

## Examples

Example courses are provided in the [examples](./examples) directory.

## Supported unit types and formats

For each unit type, we indicate whether reading from (R) and writing to (W) the corresponding format are supported.

Unit type / Format | OLX | HTML/Markdown
---|---|---
Top-level course | R+W | R+W
Title | R+W | R+W
Multiple choice question | R+W | R+W
Video | R+W | R+W
Multiple choice question | R+W | R+W
Raw HTML | R+W | R+W
iframe |  |
more to come... |  |

### Notes and known limitations

#### OLX

##### Writer

* Multiple choice questions are always rendered as checkboxes, and not as single-choice questions.

## License

This work is licensed under the terms of the [GNU Affero General Public License (AGPL)](https://github.com/overhangio/lecture/blob/master/LICENSE.txt).
