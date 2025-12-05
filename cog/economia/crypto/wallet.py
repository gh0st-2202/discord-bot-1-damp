import discord
from discord import app_commands
from typing import Optional
import os
from datetime import datetime, timedelta
from supabase import create_client
import json

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

def get_price_history():
    """Obtiene el historial de precios desde archivo JSON"""
    try:
        # Buscar el archivo en el directorio correcto
        import sys
        import os
        
        # Obtener el directorio actual del archivo
        current_dir = os.path.dirname(os.path.abspath(__file__))
        history_path = os.path.join(current_dir, "..", "crypto_price_history.json")
        
        if os.path.exists(history_path):
            with open(history_path, 'r') as f:
                return json.load(f)
        else:
            # Buscar en el directorio principal
            main_dir = os.path.join(current_dir, "..", "..")
            history_path = os.path.join(main_dir, "crypto_price_history.json")
            if os.path.exists(history_path):
                with open(history_path, 'r') as f:
                    return json.load(f)
            
            # Si no existe, crear estructura inicial
            history = {
                "BTC": {"original": 10000, "current": 10000, "change_percent": 0.0},
                "ETH": {"original": 3000, "current": 3000, "change_percent": 0.0},
                "DOG": {"original": 50, "current": 50, "change_percent": 0.0}
            }
            return history
    except Exception as e:
        print(f"❌ Error al cargar historial de precios: {e}")
        return {
            "BTC": {"original": 10000, "current": 10000, "change_percent": 0.0},
            "ETH": {"original": 3000, "current": 3000, "change_percent": 0.0},
            "DOG": {"original": 50, "current": 50, "change_percent": 0.0}
        }

def get_current_prices_with_change():
    """Obtiene precios actuales junto con porcentaje de cambio"""
    current_prices = get_current_prices()
    history = get_price_history()
    
    result = {}
    for crypto in ["BTC", "ETH", "DOG"]:
        current_price = current_prices.get(crypto, 0)
        crypto_history = history.get(crypto, {})
        
        result[crypto] = {
            'price': current_price,
            'change_percent': crypto_history.get('change_percent', 0.0),
            'original': crypto_history.get('original', current_price)
        }
    
    return result

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

def get_player_balance(discord_id):
    supabase = get_supabase_client()
    try:
        response = supabase.table('players').select('balance').eq('discord_id', discord_id).execute()
        
        if response.data:
            return response.data[0]['balance']
        else:
            supabase.table('players').insert({
                'discord_id': discord_id,
                'username': f'Usuario_{discord_id}',
                'balance': 500
            }).execute()
            return 500
    except Exception as e:
        print(f"❌ Error al obtener balance: {e}")
        return 0

# ============ COMANDO MEJORADO ============
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
        
        current_prices_data = get_current_prices_with_change()
        player_balance = get_player_balance(str(target_user.id))
        
        # Configuraciones de criptomonedas
        cryptos = {
            "BTC": {"name": "BitCord", "emoji": "₿", "color": 0xF7931A, "icon": "https://cryptologos.cc/logos/bitcoin-btc-logo.png"},
            "ETH": {"name": "Etherium", "emoji": "Ξ", "color": 0x627EEA, "icon": "https://cryptologos.cc/logos/ethereum-eth-logo.png"},
            "DOG": {"name": "DoggoCoin", "emoji": "🐕", "color": 0xF2A900, "icon": "https://cryptologos.cc/logos/dogecoin-doge-logo.png"}
        }
        
        # Calcular valores
        total_crypto_value = 0
        crypto_details = []
        market_changes = []
        
        for symbol, config in cryptos.items():
            balance = wallet.get(f'{symbol.lower()}_balance', 0.0)
            price_data = current_prices_data.get(symbol, {})
            price = price_data.get('price', 0)
            change_percent = price_data.get('change_percent', 0.0)
            original_price = price_data.get('original', price)
            
            value = balance * price
            total_crypto_value += value
            
            if balance > 0:
                crypto_details.append({
                    "symbol": symbol,
                    "balance": balance,
                    "price": price,
                    "value": value,
                    "change_percent": change_percent,
                    "original_price": original_price,
                    "config": config
                })
            
            # Guardar cambios de mercado para resumen
            market_changes.append({
                "symbol": symbol,
                "change_percent": change_percent,
                "config": config
            })
        
        # Calcular estadísticas
        invested = wallet.get('total_invested', 0)
        withdrawn = wallet.get('total_withdrawn', 0)
        net_invested = invested - withdrawn
        profit = total_crypto_value - net_invested
        profit_percent = (profit / net_invested * 100) if net_invested > 0 else 0
        
        # Determinar color principal
        if profit_percent >= 0:
            main_color = 0x00FF00
        else:
            main_color = 0xFF0000
        
        # Crear embed principal
        embed = discord.Embed(
            title=f"💰 CARTERA DE CRIPTOMONEDAS",
            description=f"**Usuario:** {target_user.mention}\n"
                       f"**ID:** `{target_user.id}`",
            color=main_color
        )
        
        # Añadir avatar del usuario
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Sección 1: Resumen de Balances
        embed.add_field(
            name="📊 RESUMEN FINANCIERO",
            value=f"**💵 Monedas Disponibles:** {player_balance:,}\n"
                  f"**💼 Valor Total en Crypto:** {total_crypto_value:,.0f}\n"
                  f"**💎 Patrimonio Total:** {player_balance + total_crypto_value:,.0f}",
            inline=False
        )
        
        # Sección 2: Rendimiento Personal
        if invested > 0 or withdrawn > 0:
            embed.add_field(
                name="📈 RENDIMIENTO PERSONAL",
                value=f"**📥 Total Invertido:** {invested:,}\n"
                      f"**📤 Total Retirado:** {withdrawn:,}\n"
                      f"**💰 Ganancia/Resultado:** {profit:+,.0f} ({profit_percent:+.1f}%)",
                inline=False
            )
        
        # Sección 3: Cambios del Mercado
        market_summary = []
        for change_data in market_changes:
            symbol = change_data["symbol"]
            change = change_data["change_percent"]
            emoji = "📈" if change >= 0 else "📉"
            market_summary.append(f"{change_data['config']['emoji']} {symbol}: {change:+.2f}% {emoji}")
        
        if market_summary:
            embed.add_field(
                name="📊 CAMBIOS DEL MERCADO",
                value=" | ".join(market_summary),
                inline=False
            )
        
        # Sección 4: Detalles por Criptomoneda
        if crypto_details:
            crypto_text = []
            for detail in crypto_details:
                config = detail["config"]
                change_emoji = "📈" if detail["change_percent"] >= 0 else "📉"
                crypto_text.append(
                    f"{config['emoji']} **{config['name']} ({detail['symbol']})**\n"
                    f"   ├ Balance: {detail['balance']:.4f}\n"
                    f"   ├ Precio Actual: {detail['price']:,}\n"
                    f"   ├ Cambio: {detail['change_percent']:+.2f}% {change_emoji}\n"
                    f"   └ Valor: {detail['value']:,.0f}"
                )
            
            embed.add_field(
                name="🔗 CRIPTOMONEDAS DETALLADAS",
                value="\n\n".join(crypto_text),
                inline=False
            )
        else:
            embed.add_field(
                name="🔗 CRIPTOMONEDAS",
                value="🚫 No tienes criptomonedas en tu wallet\n"
                      "Usa `/crypto buy` para comenzar a invertir",
                inline=False
            )
        
        # Sección 5: Consejos basados en el mercado
        tips = []
        if market_changes:
            best_performer = max(market_changes, key=lambda x: x["change_percent"])
            worst_performer = min(market_changes, key=lambda x: x["change_percent"])
            
            if best_performer["change_percent"] > 5:
                tips.append(f"💡 **Oportunidad:** {best_performer['config']['emoji']} {best_performer['symbol']} está subiendo fuerte (+{best_performer['change_percent']:.1f}%)")
            if worst_performer["change_percent"] < -5:
                tips.append(f"⚠️ **Precaución:** {worst_performer['config']['emoji']} {worst_performer['symbol']} está bajando ({worst_performer['change_percent']:.1f}%)")
        
        tips.append("⏰ **Recordatorio:** Los precios se actualizan cada 5 minutos")
        tips.append("📊 **Consejo:** Diversifica tu inversión entre diferentes criptomonedas")
        
        if tips:
            embed.add_field(
                name="💡 INFORMACIÓN ÚTIL",
                value="\n".join(tips),
                inline=False
            )
        
        # Footer con timestamp
        embed.timestamp = datetime.now()
        embed.set_footer(
            text=f"Wallet ID: {target_user.id[:8]} • Última actualización",
            icon_url="https://cdn-icons-png.flaticon.com/512/1828/1828843.png"
        )
        
        await interaction.followup.send(embed=embed, ephemeral=is_self)
