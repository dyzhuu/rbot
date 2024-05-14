import asyncio
from collections import deque
from models.SongQueue import SongQueue
from discord.ext.commands import Context

class DownloadBuffer:
    def __init__(self, bot, queue):
        self.bot = bot
        self.queue: SongQueue = queue
        self.downloaded_songs = 1
        self.is_downloading = False

    async def download_songs(self, ctx: Context):
        self.is_downloading = True
        while self.downloaded_songs < 10:
            next_song = self.queue.get_next_undownloaded_song()
            if next_song:
                next_song.downloaded = True
                await next_song.download()
                self.downloaded_songs += 1
            else:
                break  # No more songs to download
        self.is_downloading = False

    def song_finished(self):
        if self.downloaded_songs > 0:
            self.downloaded_songs -= 1

    def start_download(self, ctx: Context):
        if not self.is_downloading:
            self.bot.loop.create_task(self.download_songs(ctx))