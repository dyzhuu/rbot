from pytube import YouTube, Playlist, Search
from models.Song import YoutubeSong
import asyncio
from concurrent.futures import ThreadPoolExecutor


def get_youtube_video(url: str):
    yt = YouTube(url)

    return YoutubeSong(
        time=round(yt.length),
        url=yt.watch_url,
        title=yt.title,
        image_url=yt.thumbnail_url,
        author=yt.author
    )


def get_youtube_song(yt):
    return YoutubeSong(
        time=yt.length,
        url=yt.watch_url,
        title=yt.title,
        image_url=yt.thumbnail_url,
        author=yt.author
    )


async def get_videos_from_yt_playlist(url: str):
    if not url:
        return

    p = Playlist(url)
    with ThreadPoolExecutor() as executor:
        loop = asyncio.get_event_loop()
        futures = [loop.run_in_executor(
            executor, get_youtube_song, yt) for yt in p.videos]
        return await asyncio.gather(*futures)


def search_multiple_video(query: str):
    if not query:
        return

    s = Search(query)
    return [get_youtube_video(video.watch_url) for video in s.results[:5]]
