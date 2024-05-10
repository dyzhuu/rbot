import discord
import os
import traceback
from collections import defaultdict, deque

# from cogs.music import Music
from cogs.musiccopy import Music
from cogs.help import Help
from services.chatgpt import chatgpt_response

from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('TOKEN')

MAX_MEMORY_SIZE = 10


class DiscordClient(commands.Bot):

    def __init__(self, *, intents: discord.Intents):
        super().__init__(command_prefix="y!", help_command=None, intents=intents)
        self.memory = defaultdict(deque)

    async def setup_hook(self):
        await self.add_cog(Music(bot=self))
        await self.add_cog(Help(bot=self))

    async def on_ready(self):
        print(f'Logged in as {client.user} 🤖')

    async def on_message(self, message):
        split_message = message.content.replace('y! ', 'y!').split(' ')
        message.content = f"{split_message[0].lower()} {' '.join(split_message[1:])}"
        await self.process_commands(message)
        if message.author == client.user:
            return
        try:
            if str(message.channel.type) == 'private' or (message.mentions and message.mentions[0].id == 1137755546007646291):
                async with message.channel.typing():
                    response = chatgpt_response(
                        message.content, self.memory[message.author.id])
                    if len(self.memory[message.author.id]) > MAX_MEMORY_SIZE:
                        self.memory[message.author.id].popleft()
                    await message.reply(response, mention_author=False)
        except Exception:
            print(traceback.print_exc())


intents = discord.Intents.all()
intents.message_content = True

client = DiscordClient(intents=intents)
