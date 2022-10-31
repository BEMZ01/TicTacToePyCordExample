import discord
from discord.ext import commands


class Core(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @discord.slash_command(name="ping", description="Get the bot's latency")
    async def ping(self, ctx):
        await ctx.respond("Pong! {0}".format(round(self.bot.latency, 1)), ephemeral=True)


def setup(bot):
    bot.add_cog(Core(bot))
