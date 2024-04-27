from enum import Enum
# from typing import List
from abc import ABC, abstractmethod


class SongType(Enum):
    SPOTIFY = 1
    YOUTUBE = 2


# "title": f"{track.name} - {track.artists[0].name}",
# "album": track.album.name,
# "url": f"{track.name} - {track.artists[0].name}",
# "image_url": track.album.images[0].url,
# "song_url": track.external_urls['spotify'],
# "type": "spotify"


class Song(ABC):

    def __init__(self, file: str, time: float, url: str, title: str, image_url: str, requested_user: str, song_type: SongType):
        self.file = file
        self.time = time
        self.url = url
        self.title = title
        self.image_url = image_url
        self.requested_user = requested_user
        self.song_type = song_type

    @abstractmethod
    def download(self):
        pass


class YoutubeSong(Song):
    def __init__(self, file: str, time: float, url: str, title: str, image_url: str, requested_user: str, author: str):
        super().__init__(file, time, url, title, image_url, requested_user, SongType.YOUTUBE)
        self.author = author


class SpotifySong(Song):
    def __init__(self, file: str, time: float, url: str, title: str, image_url: str, requested_user: str, album: str, artist: str):
        super().__init__(file, time, url, title, image_url, requested_user, SongType.SPOTIFY)
        self.album = album
        self.artist = artist
