from enum import Enum
from typing import Optional
from abc import ABC, abstractmethod

from services.YTDL import YTDLSource


class SongType(Enum):
    SPOTIFY = 1
    YOUTUBE = 2


class Song(ABC):
    def __init__(self, file: str, time: int, url: str, title: str, image_url: str, requested_user: str, song_type: SongType):
        self.file: str = file
        self.time: int = time
        self.url: str = url
        self.title: str = title
        self.image_url: str = image_url
        self.requested_user: str = requested_user
        self.song_type: SongType = song_type
        self.start_time: Optional[int] = None
        self.lyrics: Optional[str] = None
        self.skipped: bool = False
        self.is_seek: bool = False

    @abstractmethod
    async def download(self):
        pass


class YoutubeSong(Song):
    def __init__(self, time: int, url: str, title: str, image_url: str, author: str, file: str = None, requested_user: str = None):
        super().__init__(file, time, url, title, image_url, requested_user, SongType.YOUTUBE)
        self.author = author

    async def download(self):
        self.file = (await YTDLSource.from_url(self.url))["file"]

    def __str__(self):
        return f"{self.title} - {self.author}"


class SpotifySong(Song):
    def __init__(self, url: str, title: str, image_url: str, album: str, artist: str, file: str = None, time: int = None, requested_user: str = None):
        super().__init__(file, time, url, title, image_url, requested_user, SongType.SPOTIFY)
        self.album = album
        self.artist = artist

    async def download(self, loop=None):
        data = await YTDLSource.from_name(f"{self.title} {self.artist}", loop=loop)
        self.file = data["file"]
        self.time = data["time"]

    def __str__(self):
        return f"{self.title} - {self.artist}"
