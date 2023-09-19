import discord
from discord.ext import commands


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='help', usage='help <command>', help='Shows this message')
    async def help(self, ctx, help_command=None):
        if not help_command:
            embed = discord.Embed(title=f'Commands')
            for cog in self.bot.cogs:
                commands = [f"`{c.name}`" for c in self.bot.get_cog(
                    cog).get_commands()]
                commands.sort()
                embed.add_field(
                    name=cog, value=f"{', '.join(commands)}", inline=False)
                embed.set_footer(
                    text="To see more info about a command, type y!help <command>")
            await ctx.send(embed=embed)
        else:
            command = self.bot.get_command(help_command)
            if command:
                embed = discord.Embed(title=command.name,
                                      description=command.help)
                embed.add_field(name=' ', value='')
                embed.add_field(
                    name='Usage', value=f'`{command.usage}`\n', inline=False)
                if command.extras:
                    embed.add_field(name=' ', value='')
                    embed.add_field(
                        name='Example', value="\n".join(command.extras["example"])+'\n', inline=False)
                if command.aliases:
                    embed.add_field(name=' ', value='')
                    embed.add_field(
                        name='Aliases', value=', '.join([f"`{a}`" for a in command.aliases]), inline=False)
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"`{help_command}` not found")
