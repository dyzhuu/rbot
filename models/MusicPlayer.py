import discord
import asyncio

from discord.ext.commands import Context

from .Enums import Loop

from models.SongQueue import SongQueue
from models.Song import YoutubeSong

from services.spotify import get_spotify_track, get_spotify_album_tracks, get_spotify_playlist_tracks
from services.youtube import get_videos_from_yt_playlist
from services.YTDL import YTDLSource

from lib.utils import convert_seconds_to_timestamp


class MusicPlayer:
    def __init__(self, bot):
        self.queue = SongQueue()
        self.bot = bot
        self.now_playing = None
        self.loop: Loop = Loop.OFF

    async def send_now_playing(self, ctx):
        time_elapsed = convert_seconds_to_timestamp(
            round(self.bot.loop.time() - self.now_playing.start_time))
        embed = discord.Embed(
            title="Now Playing", description=f'**[{self.now_playing.title}]({self.now_playing.url})**\n`[{time_elapsed} / {convert_seconds_to_timestamp(self.now_playing.time)}]`')
        embed.add_field(
            name="", value=f"Requested by: {self.now_playing.requested_user}")
        embed.set_image(url=self.now_playing.image_url)
        if not self.queue.is_empty():
            embed.set_footer(
                text=f'Up next: {self.queue[0].title}')
        await ctx.send(embed=embed)

    async def play_next(self, ctx: Context):
        self.now_playing = None
        await self.play(ctx)

    async def play(self, ctx: Context):
        if self.queue.is_empty() or ctx.voice_client.is_playing():
            return

        song = self.queue.dequeue()

        if not song.file:
            await song.download()

        self.now_playing = song

        self.now_playing.start_time = self.bot.loop.time()
        await self.send_now_playing(ctx)
        ctx.voice_client.play(
            discord.FFmpegPCMAudio(
                source=song.file, executable="./ffmpeg"),
            after=lambda e: asyncio.run_coroutine_threadsafe(
                self.play_next(ctx), self.bot.loop)
        )

    async def add_song_by_url(self, ctx, url):
        if "spotify" in url:
            song = get_spotify_track(url)
            song.requested_user = f"<@{ctx.message.author.id}>"

            data = await YTDLSource.from_name(str(song), loop=self.bot.loop)

            song.file = data["file"]
            song.time = data["time"]
        else:
            data = await YTDLSource.from_url(url)
            song = YoutubeSong(
                file=data["file"],
                time=data["time"],
                title=data["title"],
                url=data["url"],
                image_url=data["image_url"],
                requested_user=f"<@{ctx.message.author.id}>",
                author=data["author"]
            )
        self.queue.enqueue(song)

    async def add_song_by_name(self, ctx, name):
        data = await YTDLSource.from_name(name, loop=self.bot.loop)
        song = YoutubeSong(
            file=data["file"],
            time=data["time"],
            title=data["title"],
            url=data["url"],
            image_url=data["image_url"],
            requested_user=f"<@{ctx.message.author.id}>",
            author=data["author"]
        )
        self.queue.enqueue(song)

    async def add_spotify_playlist_or_album(self, ctx, url):
        if "playlist" in url:
            songs = get_spotify_playlist_tracks(url)
        elif "album" in url:
            songs = get_spotify_album_tracks(url)
        else:
            return

        for song in songs:
            song.requested_user = f"<@{ctx.message.author.id}>"
            self.queue.enqueue(song)

    async def add_youtube_playlist(self, ctx, url):
        songs = await get_videos_from_yt_playlist(url)
        for song in songs:
            song.requested_user = f"<@{ctx.message.author.id}>"
            self.queue.enqueue(song)
