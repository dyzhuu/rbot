import os
import asyncio
import random
import ctypes
import math
import time
from concurrent.futures.thread import ThreadPoolExecutor
from collections import deque
from enum import Enum

from dotenv import load_dotenv
import discord
from discord.ext import commands
import requests

from lib.constants import MAX_QUEUE_LENGTH, MAX_PLAYLIST_SONG_LENGTH
from lib.utils import delete_audio, number_emojis, convert_seconds, time_string_to_seconds
from lib.lyrics import get_lyrics
from services.spotify import search_album, search_playlist, get_videos_from_spotify_playlist, get_videos_from_spotify_album, get_spotify_track
from services.youtube import YTDLSource, get_youtube_video, get_videos_from_yt_playlist, search_multiple_video

load_dotenv()
ENVIRONMENT = os.getenv('ENVIRONMENT')

if not discord.opus.is_loaded():
    if ENVIRONMENT == "DEVELOPMENT":
        path = os.path.dirname(__file__)
        opus_path = os.path.join(path, "../opus/lib/libopus.dylib")
    elif ENVIRONMENT == "PRODUCTION":
        opus_path = ctypes.util.find_library('opus')
    discord.opus.load_opus(opus_path)


class Loop(Enum):
    OFF = 1,
    ON = 2,
    ONE = 3


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = deque()
        self.download_queue = deque()
        self.loop_state = Loop.OFF
        self.past = None
        self.now_playing = None
        self.playlist_videos = deque()
        self.start_time = None
        self.is_seek = False
        self.is_skip = False

    def play_next(self, ctx):
        voice_client = ctx.voice_client
        for v in ctx.guild.voice_channels:  # if the bot is the only one left in the channel, disconnect
            if self.bot.user in v.members and len(v.members) == 1:
                self.clear_settings()
                asyncio.run_coroutine_threadsafe(
                    ctx.voice_client.disconnect(), self.bot.loop)
                return

        self.past = self.now_playing

        if self.is_seek:  # if play is called with seek, don't play next song
            self.is_seek = False
            return

        in_voice_channel = ctx.voice_client
        if not in_voice_channel:  # if the bot is not in a voice channel, return
            return

        if self.loop_state == Loop.OFF and self.now_playing not in self.queue and os.path.exists(self.now_playing["file"]):
            os.remove(self.now_playing["file"])
        if self.loop_state == Loop.ON and not self.is_skip:
            self.queue.append(self.now_playing)
        elif self.loop_state == Loop.ONE and not self.is_skip:
            self.queue.appendleft(self.now_playing)

        if self.is_skip:
            self.is_skip = False

        self.now_playing = None

        if self.queue:  # if queue is not empty, play next song
            # TODO: Better implementation for buffer
            counter = 0
            while "file" not in self.queue[0] or not os.path.exists(self.queue[0]["file"]):
                counter += 1
                if counter > 75:
                    asyncio.run_coroutine_threadsafe(
                        self._download(ctx), self.bot.loop)
                    self.now_playing = self.past
                    self.play_next(ctx)
                    return
                time.sleep(0.2)

            self.now_playing = self.queue.popleft()
            voice_client.play(discord.FFmpegPCMAudio(
                source=self.now_playing["file"], executable="./ffmpeg"), after=lambda e: self.play_next(ctx))
            self.start_time = self.bot.loop.time()
            asyncio.run_coroutine_threadsafe(
                self._now_playing(ctx), self.bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(
                self.sleep_and_disconnect(voice_client), loop=self.bot.loop)

    # disconnects if the bot is idle for 5 minutes
    async def sleep_and_disconnect(self, voice_client):
        for _ in range(60):
            await asyncio.sleep(5)
            if voice_client.is_playing():
                return
        self.clear_settings()
        await voice_client.disconnect()

    def clear_settings(self):
        self.queue = deque()
        self.download_queue = deque()
        self.past = None
        self.now_playing = None
        self.playlist_videos = deque()
        self.start_time = None
        self.is_seek = False
        self.is_skip = False
        delete_audio()

    @commands.command(name='join', help='Joins your current voice channel', usage='join')
    async def _join(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("You're not connected to a voice channel")
            return
        else:
            channel = ctx.message.author.voice.channel
        await channel.connect()
        await self.sleep_and_disconnect(ctx.voice_client)

    @commands.command(name='disconnect', help='Disconnects from the voice channel', usage='disconnect', aliases=['dc', 'kys'])
    async def _disconnect(self, ctx):
        voice = ctx.voice_client
        await voice.disconnect()
        self.clear_settings()

    @commands.command(name='play', help='Plays a song using a url or name, accepts youtube and spotify.', aliases=['p', 'pl'], usage='play <song name or url>\nplay [album | playlist] <album/playlist name>', extras={"example": ["`play https://open.spotify.com/album/4pJT0WKggr4xk149X8A6KC`", "`play album persona 5`"]})
    async def _play(self, ctx, *args):
        if not ctx.voice_client:
            if ctx.message.author.voice:
                channel = ctx.message.author.voice.channel
                await channel.connect()
            else:
                await ctx.send("You're not connected to a voice channel")
                return

        if len(self.queue) > MAX_QUEUE_LENGTH:
            await ctx.send("Too many songs in the queue!")
            return

        if not args:
            embed = discord.Embed(
                description="**Usage:**\n- `play <song name or url>`\n- `play [album | playlist] <album/playlist name>`", color=discord.Colour.red())
            await ctx.send(embed=embed)
            return

        if args[0] == "album":  # play album
            if len(args) == 1:
                embed = discord.Embed(
                    description="**Usage:** `play album <album name>`", color=discord.Colour.red())
                await ctx.send(embed=embed)
                return
            album_name = " ".join(args[1:])
            title, url = search_album(album_name)
            await ctx.send(f"playing **[{title}]({url})**")
        elif args[0] == "playlist":  # play playlist
            if len(args) == 1:
                embed = discord.Embed(
                    description="**Usage:** `play playlist <playlist name>`", color=discord.Colour.red())
                await ctx.send(embed=embed)
                return
            playlist_name = " ".join(args[1:])
            title, url = search_playlist(playlist_name)
            await ctx.send(f"playing **[{title}]({url})**")
        elif 'spotify.link' in args[0]:
            url = requests.get(args[0]).url
        else:
            url = " ".join(args)
        if not url.startswith("https"):
            url = f"ytsearch:{url}"
        voice_client = ctx.voice_client

        playlist_videos = deque()

        def get_video_info(ctx, video_url):
            video_info = {
                **get_youtube_video(video_url),
                "requested_user": f"<@{ctx.message.author.id}>"
            }
            return video_info

        if "com/playlist" in url or "com/album" in url:
            loading_embed = discord.Embed(
                title="Loading songs...")
            loading_message = await ctx.send(embed=loading_embed)
            # downloads the first video
            if "spotify" in url:
                if "playlist" in url:
                    playlist_videos.extend(
                        get_videos_from_spotify_playlist(url))
                elif "album" in url:
                    playlist_videos.extend(
                        get_videos_from_spotify_album(url))
                if not playlist_videos:
                    await loading_message.delete()
                    await ctx.send("Result not found")
                    return
                if len(playlist_videos) + len(self.queue) > 500:
                    await loading_message.delete()
                    await ctx.send("Too many songs in the queue!")
                    return
                playlist_video = playlist_videos.popleft()
                self.queue.append({
                    **await YTDLSource.from_spotify(f"{playlist_video['title']} {playlist_video['album']}", loop=self.bot.loop),
                    "url": playlist_video["song_url"],
                    "title": playlist_video["title"],
                    "image_url": playlist_video["image_url"],
                    "requested_user": f"<@{ctx.message.author.id}>",
                    "type": "spotify"
                })
                self.queue.extend(playlist_videos)
            else:
                playlist_videos.extend(get_videos_from_yt_playlist(url))
                if not playlist_videos:
                    await loading_message.delete()
                    await ctx.send("Result not found")
                    return
                if len(playlist_videos) + len(self.queue) > 500:
                    await loading_message.delete()
                    await ctx.send("Too many songs in the queue!")
                    return
                playlist_video = playlist_videos.popleft()
                self.queue.append({
                    **await YTDLSource.from_url(playlist_video, loop=self.bot.loop),
                    "requested_user": f"<@{ctx.message.author.id}>"
                })
                with ThreadPoolExecutor() as executor:
                    video_info_list = list(executor.map(
                        lambda u: get_video_info(ctx, u), playlist_videos))
                self.queue.extend(
                    filter(lambda v: v['time'] < MAX_PLAYLIST_SONG_LENGTH, video_info_list))
            await loading_message.delete()
            embed = discord.Embed(
                title="Added to queue", description=f'**{len(playlist_videos) + 1} songs**')
            await ctx.send(embed=embed)
        else:  # run on regular url -- downloads video and adds to queue
            async with ctx.typing():
                if "spotify" in url:
                    spotify_track = get_spotify_track(url)
                    if not spotify_track:
                        await ctx.send("Invalid URL")
                        return
                    spotify_track["url"] = spotify_track["song_url"]
                    self.queue.append({
                        **spotify_track,
                        **await YTDLSource.from_spotify(f"{spotify_track['title']}", loop=self.bot.loop),
                        "requested_user": f"<@{ctx.message.author.id}>"
                    })
                else:
                    self.queue.append({
                        **await YTDLSource.from_url(url, loop=self.bot.loop),
                        "requested_user": f"<@{ctx.message.author.id}>"
                    })

        # if the bot is not playing anything, play the first song in the queue
        if not voice_client.is_playing() and not voice_client.is_paused():
            song_file = self.queue.popleft()
            self.now_playing = song_file
            if "file" not in song_file:
                async with ctx.typing():
                    if song_file['type'] == "spotify":
                        song_file.update({
                            **await YTDLSource.from_url(url=(self.queue[0]["title"]+""), loop=self.bot.loop),
                            "requested_user": f"<@{ctx.message.author.id}>"
                        })
                    else:
                        song_file.update({
                            **await YTDLSource.from_url(self.queue[0]["url"], loop=self.bot.loop),
                            "requested_user": f"<@{ctx.message.author.id}>"
                        })
            voice_client.play(discord.FFmpegPCMAudio(
                source=song_file["file"], executable="./ffmpeg"), after=lambda e: self.play_next(ctx))
            self.start_time = self.bot.loop.time()
            await self._now_playing(ctx)
        elif "com/playlist" not in url:
            song_file = self.queue[-1]
            embed = discord.Embed(
                title="Added to queue", description=f'**[{song_file["title"]}]({song_file["url"]})**\n`[{convert_seconds(song_file["time"])}]`')
            embed.set_image(url=song_file["image_url"])
            embed.set_footer(text=f'#{len(self.queue)} in queue')
            await ctx.send(embed=embed)

        if "com/playlist" not in url and "com/album" not in url:
            return
        await self._download(ctx)

    @commands.command(name='playtop', help='Adds a song to the top of the queue', aliases=['pt'], usage='playtop <song name or url>')
    async def _play_top(self, ctx, *args):
        if not ctx.voice_client:
            if ctx.message.author.voice:
                channel = ctx.message.author.voice.channel
                await channel.connect()
            else:
                await ctx.send("You're not connected to a voice channel")
                return

        if len(self.queue) > 500:
            await ctx.send("Too many songs in the queue!")
            return

        if not args:
            embed = discord.Embed(
                description="**Usage:** `playtop <song name or url>`", color=discord.Colour.red())
            await ctx.send(embed=embed)
            return
        url = " ".join(args)
        if len(args) > 1:
            url = f"ytsearch:{url}"

        voice_client = ctx.voice_client

        if "com/playlist" in url or "com/album" in url:
            await ctx.send("Cannot play playlists with `playtop`")
            return

        async with ctx.typing():
            self.queue.appendleft({
                **await YTDLSource.from_url(url, loop=self.bot.loop),
                "requested_user": f"<@{ctx.message.author.id}>"
            })

        if not ctx.voice_client.is_playing() and len(self.queue) <= 1:
            song_file = self.queue.popleft()
            self.now_playing = song_file

            voice_client.play(discord.FFmpegPCMAudio(
                source=song_file["file"], executable="./ffmpeg"), after=lambda e: self.play_next(ctx))
            self.start_time = self.bot.loop.time()
            await self._now_playing(ctx)
        else:
            song_file = self.queue[0]
            embed = discord.Embed(
                title="Added to queue", description=f'**[{song_file["title"]}]({song_file["url"]})**\n`[{convert_seconds(song_file["time"])}]`')
            embed.set_image(url=song_file["image_url"])
            embed.set_footer(text='#1 in queue')
            await ctx.send(embed=embed)

    @commands.command(name='pause', help='Pauses the song', usage='pause')
    async def _pause(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_playing():
            voice_client.pause()
            await ctx.send("Music is now paused")
        else:
            await ctx.send("Nothing is currently playing. Use y!play to play a song")

    @commands.command(name='resume', help='Resumes the song', usage='resume')
    async def _resume(self, ctx):
        voice_client = ctx.voice_client
        if voice_client.is_paused():
            voice_client.resume()
            await ctx.send("Music is now resumed")
        else:
            await ctx.send("Nothing is currently playing. Use y!play to play a song")

    @commands.command(name='skip', help='Skips the song, or skips to a specific song', usage='skip | skip <position in queue>')
    async def _skip(self, ctx, number: int = 1):
        self.is_skip = True
        voice_client = ctx.voice_client
        if number < 1 or (self.queue and number > len(self.queue)):
            await ctx.send("Invalid position in queue")
            return
        if len(self.queue) > 0:
            temp = self.queue[number - 1]
            del self.queue[number - 1]
            self.queue.appendleft(temp)
            async with ctx.typing():
                counter = 0
                while "file" not in self.queue[0] or not os.path.exists(self.queue[0]["file"]):
                    counter += 1
                    if counter > 75:
                        asyncio.run_coroutine_threadsafe(
                            self._download(ctx), self.bot.loop)
                        await self._skip(ctx, number)
                        return
                    await asyncio.sleep(0.2)

        await ctx.send(f"skipped **{self.now_playing['title']}**")
        voice_client.stop()

    @commands.command(name='loop', help='Loops the queue', aliases=['repeat'], usage='loop [on | off | one]')
    async def _loop(self, ctx, setting=None):
        if setting == "off":
            self.loop_state = Loop.OFF
            await ctx.send("Looping is now off")
        elif setting == "on":
            self.loop_state = Loop.ON
            await ctx.send("Looping is now on")
        elif setting == "one":
            self.loop_state = Loop.ONE
            await ctx.send("Looping is now set to one")
        else:
            if self.loop_state == Loop.ON:
                embed = discord.Embed(
                    title="Looping is disabled.",
                    description="Use `loop [on | off | one]` to change.", color=discord.Colour.red())
            elif self.loop_state == Loop.OFF:
                embed = discord.Embed(
                    title="Looping is enabled.",
                    description="Use `loop [on | off | one]` to change.", color=discord.Colour.red())
            else:
                embed = discord.Embed(
                    title="Looping is set to one.",
                    description="Use `loop [on | off | one]` to change.", color=discord.Colour.red())
            await ctx.send(embed=embed)

    async def send_queue_page(self, ctx, page, queue_message=None):
        queue_length = len(self.queue)
        top_page = math.ceil(len(self.queue)/20)
        queue_list = [f"{index+1}. "+i["title"]
                      for (index, i) in enumerate(self.queue)][(page-1)*20:page*20]
        embed = discord.Embed(description="**Now Playing:** " + (self.now_playing["title"] if self.now_playing else "Nothing") + (
            "\n\n**Queue:**\n" + "\n".join(queue_list) if queue_length > 0 else "\n\n**Queue is empty**"))
        if ctx.guild.icon:
            embed.set_author(
                name=f"Music Queue | {ctx.guild.name}", icon_url=ctx.guild.icon.url)
        else:
            embed.set_author(name=f"Music Queue | {ctx.guild.name}")
        if queue_length > 0:
            embed.set_footer(
                text=f"Page {page} of {top_page}")

        if not queue_message:
            queue_message = await ctx.send(embed=embed)
        else:
            await queue_message.edit(embed=embed)
        if page != 1:
            await queue_message.add_reaction("◀️")
        if page < top_page:
            await queue_message.add_reaction("▶️")

        def check(reaction):
            return reaction.message.id == queue_message.id and str(reaction.emoji) in "◀️▶️"

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60, check=check)

            await queue_message.clear_reactions()
            if reaction.emoji == "◀️":
                await self.send_queue_page(ctx, page-1, queue_message)
            elif reaction.emoji == "▶️":
                await self.send_queue_page(ctx, page+1, queue_message)
        except TimeoutError:
            if queue_message:
                await queue_message.clear_reactions()

    @commands.command(name='queue', help='Shows the current queue', aliases=['q'], usage='queue | queue <page number>')
    async def _queue_command(self, ctx, page: int = 1):
        if (self.queue and page > math.ceil(len(self.queue)/20)) or page < 1:
            await ctx.send("Invalid page number")
            return
        await self.send_queue_page(ctx, page)

    @commands.command(name='find', help='Finds a song from the queue', usage='find <name of song>')
    async def _find(self, ctx, query):
        if len(self.queue) == 0:
            await ctx.send("Queue is empty")
            return
        found = False
        for index, song in enumerate(self.queue):
            if query.lower().replace(' ', '') in song["title"].lower().replace(' ', ''):
                await ctx.send(f"**{song['title']}** is at position **{index+1}** in the queue")
                found = True
                break
        if not found:
            await ctx.send("Song not found")

    @commands.command(name='remove', help='Removes a song from the queue', aliases=['rm'], usage='remove <position in queue>')
    async def _remove(self, ctx, index):
        if len(self.queue) == 0:
            await ctx.send("Queue is empty")
            return
        if index.isdigit():
            index = int(index)
            if index < 1 or index > len(self.queue):
                await ctx.send("Invalid position in queue")
                return
        else:
            for ind, song in enumerate(self.queue):
                if index.lower().replace(' ', '') in song["title"].lower().replace(' ', ''):
                    index = ind + 1
                    break
                else:
                    await ctx.send("Song not found")
                    return
        song_file = self.queue[index - 1]
        del self.queue[index - 1]
        await ctx.send(f"removed **{song_file['title']}** from the queue")

    @commands.command(name='clear', help='Clears the queue', aliases=['c'], usage='clear')
    async def _clear(self, ctx):
        self.queue.clear()
        if self.now_playing:
            delete_audio(exclude=self.now_playing["file"])
        else:
            # TODO: clear queue status as well
            delete_audio()
        await ctx.send("Queue cleared")

    @commands.command(name='shuffle', help='Shuffles the queue', usage='shuffle')
    async def _shuffle(self, ctx):
        if len(self.queue) <= 1 or not self.now_playing or not ctx.voice_client.is_playing():
            return
        random.shuffle(self.queue)
        await ctx.send("Queue shuffled")

    @commands.command(name='search', help='Searches for a song and shows multiple options to choose from', usage='search <song name>')
    async def _search(self, ctx, *args):
        if len(self.queue) > 500:
            await ctx.send("Too many songs in the queue!")
            return
        if not args:
            embed = discord.Embed(
                description="**Usage:** `search <song name>`", color=discord.Colour.red())
            await ctx.send(embed=embed)
            return
        async with ctx.typing():
            videos = search_multiple_video(" ".join(args))
        if videos is None:
            await ctx.send("No results found")
            return
        embed = discord.Embed(title="Search Results")
        for number, video in enumerate(videos):
            embed.add_field(
                name="", value=f"{number_emojis[number]}  {video['title']} {'- '+video['author'] if video['author'] not in video['title'] else ''}\n`{convert_seconds(video['time'])}`\n", inline=False)

        message = await ctx.send(embed=embed)

        for emoji in number_emojis.values():
            await message.add_reaction(emoji)

        def check(reaction, user):
            return user == ctx.author and reaction.message.id == message.id and reaction.emoji in number_emojis.values()

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60, check=check)

            if reaction.emoji == "❌":
                await message.delete()
                return

            selected_index = list(number_emojis.values()).index(reaction.emoji)

            selected_video = videos[selected_index]

            await self._play(ctx, selected_video['url'])

        except asyncio.TimeoutError:
            await message.delete()
            return

    @commands.command(name='nowplaying', help='Shows the currently playing song', aliases=['np'], usage='nowplaying')
    async def _now_playing(self, ctx):
        if not ctx.voice_client:
            await ctx.send("I'm not in a voice channel")
        if self.now_playing:
            time_elapsed = convert_seconds(
                round(self.bot.loop.time() - self.start_time))
            embed = discord.Embed(
                title="Now Playing", description=f'**[{self.now_playing["title"]}]({self.now_playing["url"]})**\n`[{time_elapsed} / {convert_seconds(self.now_playing["time"])}]`')
            if "requested_user" in self.now_playing:
                embed.add_field(
                    name="", value=f"Requested by: {self.now_playing['requested_user']}")
            embed.set_image(url=self.now_playing["image_url"])
            if self.queue:
                embed.set_footer(text=f'Up next: {self.queue[0]["title"]}')
            await ctx.send(embed=embed)
        else:
            await ctx.send("Nothing is currently playing. Use y!play to play a song")

    @commands.command(name='seek', help='Seeks to a specific time in the song', usage='seek <duration>', extras={'example': ['`seek 1m 30s`']})
    async def _seek(self, ctx, *args):
        voice_client = ctx.voice_client
        if not args:
            embed = discord.Embed(
                description="**Usage:** `seek <duration>`\n**Example:** `seek 1m 30s`", color=discord.Colour.red())
            embed.add_field(
                name="", value="Supported durations: **s=seconds, m=minutes, h=hours**")
            await ctx.send(embed=embed)
            return
        self.is_seek = True

        if not voice_client:
            await ctx.send("I'm not in a voice channel")
            return
        if not self.now_playing:
            await ctx.send("Nothing is currently playing. Use y!play to play a song")
            return

        seek_time_seconds = time_string_to_seconds("".join(args))

        if seek_time_seconds > self.now_playing["time"] or seek_time_seconds <= 0:
            await ctx.send("Invalid time")
            return

        if voice_client.is_playing():
            voice_client.stop()

        ffmpeg_options = f"-ss {seek_time_seconds}"

        self.start_time = self.bot.loop.time() - seek_time_seconds

        voice_client.play(discord.FFmpegPCMAudio(executable="./ffmpeg", source=self.now_playing["file"],
                                                 before_options=ffmpeg_options), after=lambda e: self.play_next(ctx))
        await ctx.send(f"Seeked to `{convert_seconds(seek_time_seconds)}`")

    @commands.command(name='scrub', help='Fast forward/back by x seconds, prepend with \'-\' to go back', aliases=['ff'], usage='scrub <duration> | scrub - <duration>', extras={'example': ['`scrub 1 hour 50 seconds`', '`scrub - 1m 30s`']})
    async def _scrub(self, ctx, *args):
        voice_client = ctx.voice_client
        if not args:
            embed = discord.Embed(
                description="**Usage:** `scrub <duration>`\n**Example:** `scrub 1m 30s`", color=discord.Colour.red())
            embed.add_field(
                name="", value="Supported durations: **s=seconds, m=minutes, h=hours**")
            await ctx.send(embed=embed)
            return
        if not voice_client:
            await ctx.send("I'm not in a voice channel")
            return
        if not voice_client.is_playing():
            await ctx.send("Nothing is currently playing. Use y!play to play a song")
            return
        self.is_seek = True

        processed_args = ''.join(args).replace('-', '')
        seconds = time_string_to_seconds(processed_args)

        if args[0].startswith("-"):
            seconds *= -1

        if seconds == 0:
            await ctx.send("Invalid input")
            return

        time_elapsed = round(self.bot.loop.time() - self.start_time)
        seek_time_seconds = time_elapsed + seconds

        if seek_time_seconds > self.now_playing["time"] or seek_time_seconds <= 0:
            await ctx.send("Invalid time")
            return

        if voice_client.is_playing():
            voice_client.stop()

        ffmpeg_options = f"-ss {seek_time_seconds}"

        self.start_time = self.bot.loop.time() - seek_time_seconds

        time_elapsed = round(self.bot.loop.time() - self.start_time)

        voice_client.play(discord.FFmpegPCMAudio(executable="./ffmpeg", source=self.now_playing["file"],
                                                 before_options=ffmpeg_options), after=lambda e: self.play_next(ctx))
        embed = discord.Embed(
            description=f'**[{self.now_playing["title"]}]({self.now_playing["url"]})**\n`[{convert_seconds(time_elapsed-seconds)} / {convert_seconds(self.now_playing["time"])}]`  →  `[{convert_seconds(time_elapsed)} / {convert_seconds(self.now_playing["time"])}]`')
        await ctx.send(f"went {'forward' if seconds > 0 else 'back'} `{abs(seconds)} seconds`", embed=embed)

    @commands.command(name='poke', help='Pokes the bot', usage='poke')
    async def _poke(self, ctx):
        ctx.voice_client.pause()
        time.sleep(1.5)
        ctx.voice_client.resume()

    @commands.command(name='replay', help='Replays the last song.', aliases=['rp', 'again'], usage='replay')
    async def _replay(self, ctx):
        if self.past:
            if not ctx.voice_client.is_playing():
                await ctx.send(f"Replaying **{self.past['title']}**")
            await self._play(ctx, self.past["url"])

    async def send_lyric_page(self, ctx, page=1, message=None, sent_lyrics=None):
        if sent_lyrics:
            lyrics = sent_lyrics
        else:
            lyrics = self.now_playing['lyrics']
        top_page = len(lyrics)

        if page < 1 or page > top_page:
            await ctx.send("Invalid position")
            return

        if sent_lyrics:
            embed = discord.Embed()
        else:
            embed = discord.Embed(
                title=f"Lyrics for {self.now_playing['title']}")

        processed_lyrics = lyrics[page -
                                  1].replace('\n[', '<split>[').replace('[', '\n\n**[').replace(']', ']**').split('<split>')

        for lyric_section in processed_lyrics:
            for lyric in split_lyric(lyric_section):
                embed.add_field(name="", value=lyric, inline=False)

        embed.set_footer(text=f"Section {page}/{top_page}")
        if not message:
            message = await ctx.send(embed=embed)
        else:
            await message.edit(embed=embed)

        if page != 1:
            await message.add_reaction("◀️")
        if page < top_page:
            await message.add_reaction("▶️")

        def check(reaction, user):
            return reaction.message.id == message.id and str(reaction.emoji) in "◀️▶️"

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=150, check=check)

            await message.clear_reactions()
            if reaction.emoji == "◀️":
                await self.send_lyric_page(ctx, page-1, message=message, sent_lyrics=sent_lyrics)
            elif reaction.emoji == "▶️":
                await self.send_lyric_page(ctx, page+1, message=message, sent_lyrics=sent_lyrics)
        except TimeoutError:
            if message:
                await message.clear_reactions()

    @commands.command(name='lyrics', help='Shows the lyrics of the currently playing song', aliases=['lyric'], usage='lyrics | lyrics <song name>')
    async def _lyrics(self, ctx, *args):
        if args:
            lyrics = await self.bot.loop.run_in_executor(
                None, get_lyrics, " ".join(args))
            if not lyrics:
                await ctx.send("Lyrics not found")
                return
            await self.send_lyric_page(ctx, sent_lyrics=lyrics)
            return
        if not self.now_playing:
            await ctx.send("Nothing is currently playing. Use y!play to play a song")
            return
        if "lyrics" not in self.now_playing:
            async with ctx.typing():
                print(self.now_playing)
                if self.now_playing['type'] == "spotify":
                    song_name = self.now_playing['title']
                    lyrics = await self.bot.loop.run_in_executor(
                        None, get_lyrics, song_name)
                else:
                    song_name = f"{self.now_playing['title']}, {self.now_playing['author']}"
                    lyrics = await self.bot.loop.run_in_executor(
                        None, get_lyrics, song_name)
                    if not lyrics:
                        lyrics = await self.bot.loop.run_in_executor(
                            None, get_lyrics, self.now_playing['title'])
                print("Searching lyrics for", self.now_playing["title"])
                if not lyrics:
                    await ctx.send("Lyrics not found")
                    self.now_playing['lyrics'] = None
                    return
                self.now_playing['lyrics'] = lyrics
        await self.send_lyric_page(ctx)

    async def _download(self, ctx):
        self.download_queue = self.queue.copy()
        while self.download_queue:
            if not ctx.voice_client:
                return
            await asyncio.sleep(0.3)
            video_info = self.download_queue.popleft()
            if "file" in video_info and os.path.exists(video_info["file"]):
                continue
            if video_info["type"] == "spotify":
                buffer = await YTDLSource.from_spotify(f"{video_info['title']}", loop=self.bot.loop)
                if not buffer:
                    print('Download failed. Skipping...')
                    continue
                elif buffer['time'] > 450:
                    os.remove(buffer['file'])
                    print('Song too long. Skipping...')
                updated_video_info = {
                    "url": video_info["song_url"],
                    "requested_user": f"<@{ctx.message.author.id}>",
                    **buffer
                }
                video_info.update(updated_video_info)
            else:
                filename = await YTDLSource.from_url_download_only(video_info["url"], loop=self.bot.loop)
                if not filename:
                    print('Download failed. Skipping...')
                    continue
                video_info["file"] = filename
