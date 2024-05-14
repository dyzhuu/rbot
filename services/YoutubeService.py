from pytube import YouTube, Playlist, Search
from models.Song import YoutubeSong
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

class YoutubeService:
    @staticmethod
    def get_video(url: str) -> YoutubeSong:
        yt = YouTube(url)

        return YoutubeSong(
            time=round(yt.length),
            url=yt.watch_url,
            title=yt.title,
            image_url=yt.thumbnail_url,
            author=yt.author
        )

    @staticmethod
    def get_song(yt) -> YoutubeSong:
        return YoutubeSong(
            time=yt.length,
            url=yt.watch_url,
            title=yt.title,
            image_url=yt.thumbnail_url,
            author=yt.author
        )

    @staticmethod
    async def get_videos_from_playlist(playlist_url: str, loop=None):
        if not playlist_url:
            return

        p = Playlist(playlist_url)

        # multi-threading without blocking main event loop
        with ThreadPoolExecutor() as executor:
            event_loop = loop if loop else asyncio.get_event_loop()
            futures = [event_loop.run_in_executor(
                executor, YoutubeService.get_song, yt) for yt in p.videos]
            return await asyncio.gather(*futures)
    @staticmethod
    def search_multiple_video(query: str) -> List[YoutubeSong]:
        if not query:
            return []

        s = Search(query)
        return [YoutubeService.get_video(video.watch_url) for video in s.results[:5]]
