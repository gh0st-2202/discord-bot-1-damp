import discord
from discord import app_commands
from discord.ext import commands

class PingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="El bot dice pong")
    async def ping(self, interaction: discord.Interaction):
        """Comando ping para verificar la latencia del bot"""
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"{interaction.user.mention} me ha obligado a decir: 'pong'",
            color=discord.Color.blue(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name="📶 Latencia", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.set_footer(text="1º DAMP (BOT) • Utilidades")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PingCog(bot))
