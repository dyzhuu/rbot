from enum import Enum
# from typing import List
from abc import ABC, abstractmethod

from services.YTDL import YTDLSource


class SongType(Enum):
    SPOTIFY = 1
    YOUTUBE = 2


class Song(ABC):

    def __init__(self, file: str, time: float, url: str, title: str, image_url: str, requested_user: str, song_type: SongType):
        self.file = file
        self.time = time
        self.url = url
        self.title = title
        self.image_url = image_url
        self.requested_user = requested_user
        self.song_type = song_type
        self.start_time = None
        self.lyrics = None
        self.skipped = False

    @abstractmethod
    async def download(self):
        pass


class YoutubeSong(Song):
    def __init__(self, time: float, url: str, title: str, image_url: str, author: str, file: str = None, requested_user: str = None):
        super().__init__(file, time, url, title, image_url, requested_user, SongType.YOUTUBE)
        self.author = author

    async def download(self):
        self.file = (await YTDLSource.from_url(self.url))["file"]

    def __str__(self):
        return f"{self.title} - {self.author}"


class SpotifySong(Song):
    def __init__(self, url: str, title: str, image_url: str, album: str, artist: str, file: str = None, time: float = None, requested_user: str = None):
        super().__init__(file, time, url, title, image_url, requested_user, SongType.SPOTIFY)
        self.album = album
        self.artist = artist

    async def download(self, loop=None):
        data = await YTDLSource.from_name(f"{self.title} {self.artist}", loop=loop)
        self.file = data["file"]
        self.time = data["time"]

    def __str__(self):
        return f"{self.title} - {self.artist}"
