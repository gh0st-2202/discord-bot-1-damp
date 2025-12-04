import discord
from discord import app_commands
from typing import Optional
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

def get_or_create_crypto_wallet(discord_id):
    supabase = get_supabase_client()
    try:
        response = supabase.table('crypto_wallets').select('*').eq('discord_id', discord_id).execute()
        
        if response.data:
            return response.data[0]
        else:
            wallet_data = {
                'discord_id': discord_id,
                'btc_balance': 0.0,
                'eth_balance': 0.0,
                'dog_balance': 0.0,
                'total_invested': 0.0,
                'total_withdrawn': 0.0
            }
            
            supabase.table('crypto_wallets').insert(wallet_data).execute()
            
            response = supabase.table('crypto_wallets').select('*').eq('discord_id', discord_id).execute()
            return response.data[0]
            
    except Exception as e:
        print(f"❌ Error al obtener/crear wallet: {e}")
        return None

# ============ COMANDO ============
def setup_command(crypto_group, cog):
    @crypto_group.command(name="wallet", description="Ver tu wallet de criptomonedas o la de otro usuario")
    @app_commands.describe(usuario="Usuario para ver su wallet (opcional)")
    async def wallet(interaction: discord.Interaction, usuario: Optional[discord.User] = None):
        await interaction.response.defer(ephemeral=(usuario is None))
        
        target_user = usuario if usuario else interaction.user
        is_self = target_user.id == interaction.user.id
        
        wallet = get_or_create_crypto_wallet(str(target_user.id))
        if wallet is None:
            await interaction.followup.send("❌ Error al cargar la wallet", ephemeral=is_self)
            return
        
        current_prices = get_current_prices()
        
        # Calcular valores (enteros)
        btc_value = int(wallet.get('btc_balance', 0.0) * current_prices["BTC"])
        eth_value = int(wallet.get('eth_balance', 0.0) * current_prices["ETH"])
        dog_value = int(wallet.get('dog_balance', 0.0) * current_prices["DOG"])
        total_value = btc_value + eth_value + dog_value
        
        # Calcular ganancias
        invested = wallet.get('total_invested', 0.0)
        withdrawn = wallet.get('total_withdrawn', 0.0)
        net_invested = invested - withdrawn
        profit = total_value - net_invested if net_invested > 0 else 0
        profit_percent = (profit / net_invested * 100) if net_invested > 0 else 0
        
        # Colores y emojis
        colors = {
            "BTC": 0xF7931A,
            "ETH": 0x627EEA,
            "DOG": 0xF2A900
        }
        
        emojis = {
            "BTC": "₿",
            "ETH": "Ξ",
            "DOG": "🐕"
        }
        
        # Determinar color principal según mayor valor
        if btc_value >= eth_value and btc_value >= dog_value:
            main_color = colors["BTC"]
        elif eth_value >= dog_value:
            main_color = colors["ETH"]
        else:
            main_color = colors["DOG"]
        
        embed = discord.Embed(
            title=f"💰 Wallet de Cripto {'(Tú)' if is_self else f'de {target_user.display_name}'}",
            color=main_color
        )
        
        # Añadir balances con emojis
        wallet_text = []
        btc_balance = wallet.get('btc_balance', 0.0)
        eth_balance = wallet.get('eth_balance', 0.0)
        dog_balance = wallet.get('dog_balance', 0.0)
        
        if btc_balance > 0:
            wallet_text.append(f"{emojis['BTC']} **{btc_balance:.4f} BTC** ({btc_value:,} monedas)")
        if eth_balance > 0:
            wallet_text.append(f"{emojis['ETH']} **{eth_balance:.4f} ETH** ({eth_value:,} monedas)")
        if dog_balance > 0:
            wallet_text.append(f"{emojis['DOG']} **{dog_balance:.2f} DOG** ({dog_value:,} monedas)")
        
        if wallet_text:
            embed.add_field(
                name="📊 Balance de Cripto",
                value="\n".join(wallet_text) or "Vacío",
                inline=False
            )
        else:
            embed.add_field(
                name="📊 Balance de Cripto",
                value="💰 Wallet vacía",
                inline=False
            )
        
        # Estadísticas
        stats = [
            f"💰 **Valor Total:** {total_value:,} monedas",
            f"📈 **Ganancias:** {profit:+,.0f} monedas ({profit_percent:+.1f}%)" if net_invested > 0 else "📈 **Ganancias:** --",
            f"📥 **Total Invertido:** {invested:,.0f} monedas" if invested > 0 else "",
            f"📤 **Total Retirado:** {withdrawn:,.0f} monedas" if withdrawn > 0 else ""
        ]
        
        embed.add_field(
            name="📈 Estadísticas",
            value="\n".join([s for s in stats if s]),
            inline=False
        )
        
        # Cooldowns
        cooldown_info = []
        now = datetime.now().astimezone()
        
        for crypto in ["BTC", "ETH", "DOG"]:
            last_trade_str = wallet.get(f'last_{crypto.lower()}_trade')
            
            if last_trade_str:
                try:
                    last_trade = datetime.fromisoformat(last_trade_str.replace('Z', '+00:00'))
                    next_trade = last_trade + timedelta(hours=1)
                    if now < next_trade:
                        minutes_left = int((next_trade - now).total_seconds() / 60)
                        cooldown_info.append(f"{crypto}: {minutes_left}m")
                except:
                    pass
        
        if cooldown_info:
            embed.add_field(
                name="⏰ Cooldowns Activos",
                value=", ".join(cooldown_info),
                inline=False
            )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        embed.set_footer(text="Usa /crypto buy/sell para operar")
        
        await interaction.followup.send(embed=embed, ephemeral=is_self)
