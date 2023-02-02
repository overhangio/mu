import re
import typing as t


def is_video_url(url: str) -> bool:
    return get_video_id(url) is not None


def is_embed_url(url: str) -> bool:
    return get_embed_video_id(url) is not None


def get_watch_url(youtube_id: str) -> str:
    return f"https://www.youtube.com/watch?v={youtube_id}"


def get_embed_url(url: str) -> t.Optional[str]:
    video_id = get_video_id(url)
    if video_id is None:
        return None
    return f"https://www.youtube.com/embed/{video_id}"


def get_video_id(url: str) -> t.Optional[str]:
    match = re.match(
        r"https?://(www\.)?(youtube\.com/watch\?v=|youtu.be/)(?P<id>[a-zA-Z0-9_]+)(&.*)?$",
        url,
    )
    return None if match is None else match.group("id")


def get_embed_video_id(url: str) -> t.Optional[str]:
    match = re.match(
        r"https?://(www\.)?youtube\.com/embed/(?P<id>[a-zA-Z0-9_]+)(&.*)?$",
        url,
    )
    return None if match is None else match.group("id")
