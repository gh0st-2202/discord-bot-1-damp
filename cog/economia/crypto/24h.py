import discord
from discord import app_commands
import os
from datetime import datetime, timedelta
from supabase import create_client

# ============ FUNCIONES INDEPENDIENTES ============
def get_supabase_client():
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("❌ Faltan variables de entorno SUPABASE_URL o SUPABASE_KEY")
    
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def get_current_prices():
    supabase = get_supabase_client()
    try:
        response = supabase.table('crypto_current_prices').select('*').execute()
        
        if not response.data:
            return {"BTC": 10000, "ETH": 3000, "DOG": 50}
        
        prices = {}
        for item in response.data:
            prices[item['crypto']] = int(item['price'])
        
        for crypto in ["BTC", "ETH", "DOG"]:
            if crypto not in prices:
                prices[crypto] = {"BTC": 10000, "ETH": 3000, "DOG": 50}[crypto]
        
        return prices
    except Exception as e:
        print(f"❌ Error al obtener precios: {e}")
        return {"BTC": 10000, "ETH": 3000, "DOG": 50}

# ============ COMANDO SIMPLE ============
def setup_command(crypto_group, cog):
    @crypto_group.command(name="24h", description="Ver precio actual de una criptomoneda")
    @app_commands.describe(moneda="Criptomoneda para ver su precio")
    @app_commands.choices(
        moneda=[
            app_commands.Choice(name="BitCord (BTC)", value="BTC"),
            app_commands.Choice(name="Etherium (ETH)", value="ETH"),
            app_commands.Choice(name="DoggoCoin (DOG)", value="DOG")
        ]
    )
    async def price_single(interaction: discord.Interaction, moneda: str):
        """Muestra el precio actual de una criptomoneda específica"""
        await interaction.response.defer()
        
        crypto_symbol = moneda.upper()
        
        # Configuración de criptomonedas
        configs = {
            "BTC": {"name": "BitCord", "emoji": "₿", "color": 0xF7931A},
            "ETH": {"name": "Etherium", "emoji": "Ξ", "color": 0x627EEA},
            "DOG": {"name": "DoggoCoin", "emoji": "🐕", "color": 0xF2A900}
        }
        
        if crypto_symbol not in configs:
            await interaction.followup.send("❌ Criptomoneda no válida", ephemeral=True)
            return
        
        config = configs[crypto_symbol]
        prices = get_current_prices()
        current_price = prices.get(crypto_symbol, 0)
        
        # Crear embed simple
        embed = discord.Embed(
            title=f"{config['emoji']} {config['name']} ({crypto_symbol})",
            description=f"**Precio actual:** {current_price:,} monedas",
            color=config["color"]
        )
        
        embed.add_field(
            name="📊 Información",
            value=f"• Moneda: {config['name']}\n"
                  f"• Símbolo: {crypto_symbol}\n"
                  f"• Precio actual: **{current_price:,} monedas**\n"
                  f"• Actualizado: Ahora",
            inline=False
        )
        
        embed.set_footer(text="Los precios se actualizan cada 5 minutos")
        
        await interaction.followup.send(embed=embed)
