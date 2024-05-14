import os
import asyncio
import ctypes
import math

from dotenv import load_dotenv
import discord
from discord.ext import commands

from lib.constants import MAX_QUEUE_LENGTH
from lib.utils import number_emojis, convert_seconds_to_timestamp, \
    time_string_to_seconds, clear_audio_files
from lib.lyrics import get_lyrics, split_lyric
from lib.embeds import generate_add_to_queue_embed

from services.YoutubeService import YoutubeService

from models.MusicPlayer import MusicPlayer
from models.SongQueue import SongQueue
from models.Enums import Loop
from models.Exceptions import MessageException, LyricNotFoundException

load_dotenv()
ENVIRONMENT = os.getenv('ENVIRONMENT')

if not discord.opus.is_loaded():
    if ENVIRONMENT == "DEVELOPMENT":
        path = os.path.dirname(__file__)
        opus_path = os.path.join(path, "../opus/lib/libopus.dylib")
    else:
        opus_path = ctypes.util.find_library('opus')
    discord.opus.load_opus(opus_path)


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.queue = SongQueue()
        self.player = MusicPlayer(bot, self.queue)

    # disconnects if the bot is idle for 5 minutes
    async def sleep_and_disconnect(self, voice_client):
        for _ in range(60):
            await asyncio.sleep(5)
            if voice_client.is_playing():
                return
        self.player.reset()
        await voice_client.disconnect()

    @commands.command(name='join', help='Joins your current voice channel',
                      usage='join')
    async def _join(self, ctx):
        if not ctx.message.author.voice:
            await ctx.send("You're not connected to a voice channel")
            return
        else:
            channel = ctx.message.author.voice.channel
        await channel.connect()
        await self.sleep_and_disconnect(ctx.voice_client)

    @commands.command(name='disconnect',
                      help='Disconnects from the voice channel',
                      usage='disconnect', aliases=['dc', 'kys'])
    async def _disconnect(self, ctx):
        voice = ctx.voice_client
        await voice.disconnect()
        self.player.reset()

    @commands.command(name='play',
                      help='Plays a song using a url or name, accepts youtube and spotify.',
                      aliases=['p', 'pl'],
                      usage='play <song name or url>\nplay [album | playlist] <album/playlist name>',
                      extras={"example": [
                          "`play https://open.spotify.com/album/4pJT0WKggr4xk149X8A6KC`",
                          "`play album persona 5`"]})
    async def _play(self, ctx, *args):
        if not ctx.voice_client:
            if ctx.message.author.voice:
                channel = ctx.message.author.voice.channel
                await channel.connect()
            else:
                return await ctx.send("You're not connected to a voice channel")

        if len(self.queue) > MAX_QUEUE_LENGTH:
            return await ctx.send("Too many songs in the queue!")

        if not args:
            embed = discord.Embed(
                description="**Usage:**\n- `play <song name or url>`\n- `play [album | playlist] <album/playlist name>`",
                color=discord.Colour.red())
            return await ctx.send(embed=embed)

        if not args[0].startswith("http"):
            # album
            async with ctx.typing():
                await self.player.add_song_by_name(ctx, ' '.join(args))
        else:
            url = args[0]
            if "com/playlist" in url or "com/album" in url:
                loading_embed = discord.Embed(
                    title="Loading songs...")
                loading_message = await ctx.send(embed=loading_embed)
                try:
                    if "spotify" in url:
                        await self.player.add_spotify_playlist_or_album(ctx,
                                                                        url)
                    else:
                        await self.player.add_youtube_playlist(ctx, url)
                except MessageException as e:
                    await ctx.send(e)
                except Exception as e:
                    print(e)
                finally:
                    await loading_message.delete()
            else:
                async with ctx.typing():
                    await self.player.add_song_by_url(ctx, url)
        if self.player.now_playing:
            embed = generate_add_to_queue_embed(
                self.queue[-1], len(self.queue))
            await ctx.send(embed=embed)

        await self.player.play(ctx)

    @commands.command(name='playtop',
                      help='Adds a song to the top of the queue',
                      aliases=['pt'], usage='playtop <song name or url>')
    async def _play_top(self, ctx, *args):
        if not ctx.voice_client:
            if ctx.message.author.voice:
                channel = ctx.message.author.voice.channel
                await channel.connect()
            else:
                return await ctx.send("You're not connected to a voice channel")

        if len(self.queue) > MAX_QUEUE_LENGTH:
            return await ctx.send("Too many songs in the queue!")

        if not args:
            embed = discord.Embed(
                description="**Usage:** `playtop <song name or url>`",
                color=discord.Colour.red())
            return await ctx.send(embed=embed)

        query = " ".join(args)

        if not query.startswith("http"):
            await self.player.add_song_by_name(ctx, query, top=True)
        elif "com/playlist" in query or "com/album" in query:
            return await ctx.send("Cannot play playlists with `playtop`")
        else:
            await self.player.add_song_by_url(ctx, query, top=True)

        if self.player.now_playing:
            embed = generate_add_to_queue_embed(
                self.queue[-1], 1)
            await ctx.send(embed=embed)

        await self.player.play(ctx)

    @commands.command(name='skip',
                      help='Skips the song, or skips to a specific song',
                      usage='skip | skip <position in queue>')
    async def _skip(self, ctx, number: int = 1):
        voice_client = ctx.voice_client
        if number < 1 or number > max(len(self.queue), 1):
            return await ctx.send("Invalid position in queue")
        if number > 1:
            self.queue.move_to_front(number - 1)

        self.player.now_playing.skipped = True

        await ctx.send(f"skipped **{self.player.now_playing.title}**")
        voice_client.stop()

    @commands.command(name='loop', help='Loops the queue', aliases=['repeat'],
                      usage='loop [on | off | one]')
    async def _loop(self, ctx, setting=None):
        if setting == "off":
            self.player.loop = Loop.OFF
            return await ctx.send("Looping is now off")
        if setting == "on":
            self.player.loop = Loop.ON
            return await ctx.send("Looping is now on")
        if setting == "one":
            self.player.loop = Loop.ONE
            return await ctx.send("Looping is now set to one")

        embed = discord.Embed(
            title=f"Looping is set to {self.player.loop.name}.",
            description="Use `loop [on | off | one]` to change.",
            color=discord.Colour.red())
        await ctx.send(embed=embed)

    @commands.command(name='queue', help='Shows the current queue',
                      aliases=['q'], usage='queue | queue <page number>')
    async def _queue(self, ctx, page: int = 1):
        if (self.queue and page > math.ceil(
                len(self.queue) / 20)) or page < 1:
            return await ctx.send("Invalid page number")
        await self.send_queue_page(ctx, page)

    async def send_queue_page(self, ctx, page, prev_message=None):
        queue_length = len(self.queue)
        max_page = math.ceil(queue_length / 20)
        queue_list = [f"{index + 1}. " + str(song)
                      for (index, song) in enumerate(self.queue.queue)][
                     (page - 1) * 20:page * 20]

        embed = discord.Embed(description="**Now Playing:** " + (
            str(self.player.now_playing) if self.player.now_playing else "Nothing") + (
                                              "\n\n**Queue:**\n" + "\n".join(
                                                  queue_list) if queue_length > 0 else "\n\n**Queue is empty**"))

        if ctx.guild.icon:
            embed.set_author(
                name=f"Music Queue | {ctx.guild.name}",
                icon_url=ctx.guild.icon.url)
        else:
            embed.set_author(name=f"Music Queue | {ctx.guild.name}")

        if queue_length > 0:
            embed.set_footer(
                text=f"Page {page} of {max_page}   |   {queue_length} songs in queue")

        if not prev_message:
            prev_message = await ctx.send(embed=embed)
        else:
            await prev_message.edit(embed=embed)
        if page != 1:
            await prev_message.add_reaction("◀️")
        if page < max_page:
            await prev_message.add_reaction("▶️")

        def check(user_reaction, _):
            return user_reaction.message.id == prev_message.id and str(
                user_reaction.emoji) in "◀️▶️"

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60,
                                                  check=check)

            await prev_message.clear_reactions()

            if reaction.emoji == "◀️":
                await self.send_queue_page(ctx, page - 1, prev_message)
            elif reaction.emoji == "▶️":
                await self.send_queue_page(ctx, page + 1, prev_message)
        except TimeoutError:
            if prev_message:
                await prev_message.clear_reactions()

    @commands.command(name='find', help='Finds a song from the queue',
                      usage='find <name of song>')
    async def _find(self, ctx, query):
        if self.queue.is_empty():
            return await ctx.send("Queue is empty")
        index, song = self.queue.get_song_by_name(query)
        if not song:
            return await ctx.send("Song not found")
        return await ctx.send(
            f"**{song.title}** is at position **{index + 1}** in the queue")

    @commands.command(name='remove', help='Removes a song from the queue',
                      aliases=['rm'], usage='remove <position in queue>')
    async def _remove(self, ctx, query: str):
        if self.queue.is_empty():
            return await ctx.send("Queue is empty")
        if query.isdigit():
            index = int(query)
            if index < 1 or index > len(self.queue):
                return await ctx.send("Invalid position in queue")
            song = self.queue[index - 1]
        else:
            index, song = self.queue.get_song_by_name(query)
            if not song:
                return await ctx.send("Song not found")

        self.queue.remove(index)

        await ctx.send(f"removed **{song.title}** from the queue")

    @commands.command(name='clear', help='Clears the queue', aliases=['c'],
                      usage='clear')
    async def _clear(self, ctx):
        self.queue.clear()
        if self.player.now_playing:
            clear_audio_files(exclude=self.player.now_playing.file)
        else:
            clear_audio_files()
        await ctx.send("Queue cleared")

    @commands.command(name='shuffle', help='Shuffles the queue',
                      usage='shuffle')
    async def _shuffle(self, ctx):
        if not ctx.voice_client.is_playing() or len(self.queue) <= 1:
            return
        self.queue.shuffle()
        await ctx.send("Queue shuffled")

    @commands.command(name='search',
                      help='Searches for a song and shows multiple options to choose from',
                      usage='search <song name>')
    async def _search(self, ctx, *args):
        if len(self.queue) > MAX_QUEUE_LENGTH:
            return await ctx.send("Too many songs in the queue!")
        if not args:
            embed = discord.Embed(
                description="**Usage:** `search <song name>`",
                color=discord.Colour.red())
            return await ctx.send(embed=embed)
        async with ctx.typing():
            videos = YoutubeService.search_multiple_video(" ".join(args))
        if not videos:
            return await ctx.send("No results found")

        embed = discord.Embed(title="Search Results")
        for idx, video in enumerate(videos):
            embed.add_field(
                name="",
                value=f"{number_emojis[idx]}  {video}\n`{convert_seconds_to_timestamp(video.time)}`\n",
                inline=False)

        message = await ctx.send(embed=embed)

        for emoji in number_emojis.values():
            await message.add_reaction(emoji)

        def check(user_reaction, user):
            return user == ctx.author and user_reaction.message.id == message.id and user_reaction.emoji in number_emojis.values()

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=60,
                                                  check=check)

            if reaction.emoji == "❌":
                return await message.delete()


            selected_index = list(number_emojis.values()).index(reaction.emoji)

            selected_video = videos[selected_index]

            await self._play(ctx, selected_video.url)

        except asyncio.TimeoutError:
            return await message.delete()

    @commands.command(name='nowplaying',
                      help='Shows the currently playing song', aliases=['np'],
                      usage='nowplaying')
    async def _now_playing(self, ctx):
        if not self.player.now_playing:
            return await ctx.send(
                "Nothing is currently playing. Use y!play to play a song")
        await self.player.send_now_playing(ctx)

    @commands.command(name='seek', help='Seeks to a specific time in the song',
                      usage='seek <duration>',
                      extras={'example': ['`seek 1m 30s`']})
    async def _seek(self, ctx, *args):
        if not ctx.voice_client:
            return await ctx.send("I'm not in a voice channel")
        if not args:
            embed = discord.Embed(
                description="**Usage:** `seek <duration>`\n**Example:** `seek 1m 30s`",
                color=discord.Colour.red())
            embed.add_field(
                name="",
                value="Supported durations: **s=seconds, m=minutes, h=hours**")
            return await ctx.send(embed=embed)

        if not ctx.voice_client.is_playing():
            return await ctx.send(
                "Nothing is currently playing. Use y!play to play a song")

        seek_time_seconds = time_string_to_seconds("".join(args))

        if seek_time_seconds > self.player.now_playing.time or seek_time_seconds <= 0:
            return await ctx.send("Invalid time")

        await self.player.skip_to(ctx, seek_time_seconds)

        return await ctx.send(
            f"Seeked to `{convert_seconds_to_timestamp(seek_time_seconds)}`")

    @commands.command(name='scrub',
                      help='Fast forward/back by x seconds, prepend with \'-\' to go back',
                      aliases=['ff'],
                      usage='scrub <duration> | scrub - <duration>', extras={
            'example': ['`scrub 1 hour 50 seconds`', '`scrub - 1m 30s`']})
    async def _scrub(self, ctx, *args):
        if not ctx.voice_client:
            return await ctx.send("I'm not in a voice channel")
        if not args:
            embed = discord.Embed(
                description="**Usage:** `scrub <duration>`\n**Example:** `scrub 1m 30s`",
                color=discord.Colour.red())
            embed.add_field(
                name="",
                value="Supported durations: **s=seconds, m=minutes, h=hours**")
            return await ctx.send(embed=embed)
        if not ctx.voice_client.is_playing():
            return await ctx.send(
                "Nothing is currently playing. Use y!play to play a song")

        processed_args = ''.join(args).replace('-', '')
        seconds = time_string_to_seconds(processed_args)

        if args[0].startswith("-"):
            seconds *= -1

        if seconds == 0:
            return await ctx.send("Invalid input")

        time_elapsed = round(
            self.bot.loop.time() - self.player.now_playing.start_time)
        seek_time_seconds = time_elapsed + seconds

        if seek_time_seconds > self.player.now_playing.time or seek_time_seconds <= 0:
            return await ctx.send("Invalid time")

        await self.player.skip_to(ctx, seek_time_seconds)

        now_playing = self.player.now_playing

        time_elapsed = round(self.bot.loop.time() - now_playing.start_time)

        embed = discord.Embed(
            description=f'**[{now_playing.title}]({now_playing.url})**\n`[{convert_seconds_to_timestamp(time_elapsed - seconds)} / {convert_seconds_to_timestamp(now_playing.time)}]`  →  `[{convert_seconds_to_timestamp(time_elapsed)} / {convert_seconds_to_timestamp(now_playing.time)}]`')
        await ctx.send(
            f"Scrubbed {'forward' if seconds > 0 else 'back'} `{abs(seconds)} seconds`",
            embed=embed)

    @commands.command(name='poke', help='Pokes the bot', usage='poke')
    async def _poke(self, ctx):
        await ctx.send("hi")
        ctx.voice_client.pause()
        await asyncio.sleep(1.5)
        ctx.voice_client.resume()

    @commands.command(name='replay', help='Replays the last song.',
                      aliases=['rp', 'again'], usage='replay')
    async def _replay(self, ctx):
        past = self.player.past
        if past:
            if not ctx.voice_client.is_playing():
                await ctx.send(f"Replaying **{past.title}**")
            await self._play_top(ctx, past.url)

    @commands.command(name='lyrics',
                      help='Shows the lyrics of the currently playing song',
                      aliases=['lyric'], usage='lyrics | lyrics <song name>')
    async def _lyrics(self, ctx, *args):
        try:
            async with ctx.typing():
                if args:
                    query = " ".join(args)
                    lyrics = await self.bot.loop.run_in_executor(
                        None, get_lyrics, query)
                    return await self.send_lyric_page(ctx, lyrics, query)

                current_song = self.player.now_playing

                if not current_song:
                    return await ctx.send(
                        "Nothing is currently playing. Use y!play to play a song")

                if not current_song.lyrics:
                    lyrics = await self.bot.loop.run_in_executor(
                        None, get_lyrics, str(current_song))
                    current_song.lyrics = lyrics

            return await self.send_lyric_page(ctx, lyrics=current_song.lyrics,
                                              title=str(current_song))
        except LyricNotFoundException:
            return await ctx.send("Lyrics not found")

    async def send_lyric_page(self, ctx, lyrics, title, page=1, message=None):
        max_page = len(lyrics)

        if page < 1 or page > max_page:
            return await ctx.send("Invalid position")

        processed_lyrics = lyrics[page -
                                  1].replace('\n[', '<split>[').replace('[',
                                                                        '\n\n**[').replace(
            ']', ']**').split('<split>')

        embed = discord.Embed(
            title=f"Lyrics for {title}")

        for lyric_section in processed_lyrics:
            for lyric in split_lyric(lyric_section):
                embed.add_field(name="", value=lyric, inline=False)

        embed.set_footer(text=f"Section {page}/{max_page}")

        if not message:
            message = await ctx.send(embed=embed)
        else:
            await message.edit(embed=embed)

        if page != 1:
            await message.add_reaction("◀️")
        if page < max_page:
            await message.add_reaction("▶️")

        def check(user_reaction, _):
            return user_reaction.message.id == message.id and str(
                user_reaction.emoji) in "◀️▶️"

        try:
            reaction, _ = await self.bot.wait_for('reaction_add', timeout=150,
                                                  check=check)

            await message.clear_reactions()
            if reaction.emoji == "◀️":
                await self.send_lyric_page(ctx, lyrics, title, page - 1,
                                           message)
            elif reaction.emoji == "▶️":
                await self.send_lyric_page(ctx, lyrics, title, page + 1,
                                           message)
        except TimeoutError:
            if message:
                return await message.clear_reactions()