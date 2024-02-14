import discord
import os
import asyncio
import aiohttp
import random
import requests
import ctypes

from cogs.music import Music
from cogs.help import Help
from chatgpt import chatgpt_response

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')

MAX_MEMORY_SIZE = 10


class DiscordClient(commands.Bot):

    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="y!", help_command=None, intents=intents)
        self.memory = {}

    async def on_ready(self):
        print(f'Logged in as {client.user} 🤖')

    async def on_message(self, message):
        message.content = (message.content[:10].lower(
        ) + message.content[10:]).replace('y! ', 'y!')
        await self.process_commands(message)
        if message.author == client.user:
            return
        try:
            if str(message.channel.type) == 'private' or message.mentions[0].id == 1137755546007646291:
                if message.author.id not in self.memory:
                    self.memory[message.author.id] = []
                async with message.channel.typing():
                    response = chatgpt_response(
                        message.content, self.memory[message.author.id])
                    await message.reply(response, mention_author=False)
                print(self.memory[message.author.id])

                if len(self.memory[message.author.id]) > MAX_MEMORY_SIZE:
                    self.memory[message.author.id] = self.memory[message.author.id][-MAX_MEMORY_SIZE:]
        except Exception as e:
            # print('Error:', e)
            pass


intents = discord.Intents.all()
intents.message_content = True

client = DiscordClient(intents=intents)

asyncio.run(client.add_cog(Music(bot=client)))
asyncio.run(client.add_cog(Help(bot=client)))
