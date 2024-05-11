import yt_dlp
import discord
import asyncio
import difflib

from ytmusicapi import YTMusic

ydl_opts = {
    'format': 'bestaudio/best',
    'merge_output_format': 'opus',
    'outtmpl': "./lib/audio/%(id)s.opus",
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ydl_opts)

yt_music = YTMusic()


def download_youtube_audio(url: str, download=True):
    data = ytdl.extract_info(url, download=download)
    if 'entries' in data:
        data = data['entries'][0]
    return data


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, download_youtube_audio, url)

        return {
            "file": ytdl.prepare_filename(data),
            "url": data['original_url'],
            "title": data['title'],
            "author": data['uploader'],
            "image_url": data['thumbnail'],
            "time": round(data['duration'])
        }

    @classmethod
    async def from_name(cls, query, *, loop=None):
        loop = loop or asyncio.get_event_loop()

        result = yt_music.search(
            query, filter='songs', limit=1)

        if not result:
            raise Exception("No results found")

        videoId = result[0].get('videoId')

        data = await loop.run_in_executor(None, download_youtube_audio, f"https://www.youtube.com/watch?v={videoId}")

        return {
            "file": ytdl.prepare_filename(data),
            "url": data['original_url'],
            "title": data['title'],
            "author": data['uploader'],
            "image_url": data['thumbnail'],
            "time": round(data['duration'])
        }
