import discord
from discord import app_commands
import os
from datetime import datetime
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
                'total_invested': 0,
                'total_withdrawn': 0
            }
            
            supabase.table('crypto_wallets').insert(wallet_data).execute()
            
            response = supabase.table('crypto_wallets').select('*').eq('discord_id', discord_id).execute()
            return response.data[0] if response.data else None
            
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

def update_player_balance(discord_id, amount):
    supabase = get_supabase_client()
    try:
        current_balance = get_player_balance(discord_id)
        new_balance = current_balance + amount
        
        supabase.table('players').update({
            'balance': new_balance
        }).eq('discord_id', discord_id).execute()
        
        return True
    except Exception as e:
        print(f"❌ Error al actualizar balance: {e}")
        return False

def update_crypto_balance(discord_id, crypto, amount, total_earnings=None):
    supabase = get_supabase_client()
    try:
        wallet = get_or_create_crypto_wallet(discord_id)
        if not wallet:
            return False
        
        crypto_column = f'{crypto.lower()}_balance'
        current_balance = wallet.get(crypto_column, 0.0)
        new_balance = current_balance + amount
        
        update_data = {crypto_column: new_balance}
        
        if total_earnings is not None:
            if amount < 0:  # Venta (amount negativo)
                current_withdrawn = wallet.get('total_withdrawn', 0)
                update_data['total_withdrawn'] = int(current_withdrawn + total_earnings)
        
        supabase.table('crypto_wallets').update(update_data).eq('discord_id', discord_id).execute()
        return True
    except Exception as e:
        print(f"❌ Error al actualizar balance de cripto: {e}")
        return False

# ============ FUNCIONES PARA ACTUALIZAR LEADERBOARD ============
def get_leaderboard(limit=10):
    """Obtiene el leaderboard desde Supabase"""
    supabase = get_supabase_client()
    try:
        response = supabase.table("players").select("username, balance").order("balance", desc=True).limit(limit).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Error en get_leaderboard: {e}")
        return []

async def update_global_leaderboard(bot):
    """Actualiza el leaderboard global en el canal especificado"""
    CHANNEL_LEADERBOARD_ID = os.getenv("CHANNEL_LEADERBOARD_ID")
    
    if not CHANNEL_LEADERBOARD_ID:
        print("⚠️  CHANNEL_LEADERBOARD_ID no configurado")
        return None
    
    try:
        channel_id = int(CHANNEL_LEADERBOARD_ID)
        channel = bot.get_channel(channel_id)
        
        if not channel:
            print(f"❌ Canal de leaderboard no encontrado (ID: {channel_id})")
            return None
        
        leaderboard = get_leaderboard(10)
        
        # Intentar borrar mensajes anteriores (opcional)
        try:
            await channel.purge()
        except:
            print("⚠️  No se pudo purgar el canal, enviando nuevo mensaje")
        
        embed = discord.Embed(
            title="🏆 TABLA DE LÍDERES GLOBAL - CRIPTOMONEDAS",
            description="Ranking de jugadores por monedas totales",
            color=discord.Color.gold()
        )
        
        if not leaderboard:
            embed.description = "📭 No hay jugadores registrados todavía."
        else:
            for i, player in enumerate(leaderboard[:10], start=1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                embed.add_field(
                    name=f"{medal} {player['username']}", 
                    value=f"```{player['balance']:,} monedas```", 
                    inline=False
                )
        
        # Obtener estadísticas adicionales
        try:
            total_response = supabase.table("players").select("balance").execute()
            total_players = len(total_response.data) if total_response.data else 0
            total_wealth = sum(p["balance"] for p in total_response.data) if total_response.data else 0
            
            embed.add_field(
                name="📊 ESTADÍSTICAS GLOBALES",
                value=(
                    f"**Jugadores totales:** {total_players}\n"
                    f"**Riqueza total:** {total_wealth:,} monedas\n"
                    f"**Promedio por jugador:** {total_wealth//total_players if total_players > 0 else 0:,}"
                ),
                inline=False
            )
        except:
            pass
        
        embed.set_footer(text="Actualizado automáticamente después de cada transacción")
        embed.timestamp = datetime.now()
        
        await channel.send(embed=embed)
        
        print(f"✅ Leaderboard actualizado en el canal {channel_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando leaderboard: {e}")
        return None

# ============ COMANDO MEJORADO ============
def setup_command(crypto_group, cog):
    @crypto_group.command(name="sell", description="Vender criptomonedas")
    @app_commands.describe(
        moneda="Criptomoneda a vender",
        cantidad="Cantidad a vender"
    )
    @app_commands.choices(
        moneda=[
            app_commands.Choice(name="BitCord (BTC)", value="BTC"),
            app_commands.Choice(name="Etherium (ETH)", value="ETH"),
            app_commands.Choice(name="DoggoCoin (DOG)", value="DOG")
        ]
    )
    async def sell(interaction: discord.Interaction, moneda: str, cantidad: float):
        await interaction.response.defer(ephemeral=True)
        
        if cantidad <= 0:
            await interaction.followup.send("❌ La cantidad debe ser mayor que 0", ephemeral=True)
            return
        
        crypto_symbol = moneda.upper()
        
        # Configuraciones mejoradas
        configs = {
            "BTC": {"name": "BitCord", "emoji": "₿", "color": 0xF7931A, "icon": "https://cryptologos.cc/logos/bitcoin-btc-logo.png"},
            "ETH": {"name": "Etherium", "emoji": "Ξ", "color": 0x627EEA, "icon": "https://cryptologos.cc/logos/ethereum-eth-logo.png"},
            "DOG": {"name": "DoggoCoin", "emoji": "🐕", "color": 0xF2A900, "icon": "https://cryptologos.cc/logos/dogecoin-doge-logo.png"}
        }
        
        if crypto_symbol not in configs:
            await interaction.followup.send("❌ Criptomoneda no válida", ephemeral=True)
            return
        
        config = configs[crypto_symbol]
        
        # Obtener precios con cambio porcentual
        prices_data = get_current_prices_with_change()
        crypto_data = prices_data.get(crypto_symbol, {})
        current_price = crypto_data.get('price', 0)
        market_change_percent = crypto_data.get('change_percent', 0.0)
        original_price = crypto_data.get('original', current_price)
        
        wallet = get_or_create_crypto_wallet(str(interaction.user.id))
        
        if wallet is None:
            await interaction.followup.send("❌ Error al acceder a tu wallet", ephemeral=True)
            return
        
        if current_price <= 0:
            await interaction.followup.send("❌ Error: Precio inválido", ephemeral=True)
            return
        
        # Verificar balance de cripto
        crypto_column = f"{crypto_symbol.lower()}_balance"
        current_balance = wallet.get(crypto_column, 0.0)
        
        if current_balance < cantidad:
            embed = discord.Embed(
                title="❌ Saldo Insuficiente",
                description=f"No tienes suficiente {config['name']} para vender.",
                color=0xFF0000
            )
            embed.add_field(name=f"💰 Saldo {crypto_symbol}", value=f"{current_balance:.4f}", inline=True)
            embed.add_field(name="📤 Intentas vender", value=f"{cantidad:.4f}", inline=True)
            embed.add_field(name="📉 Faltante", value=f"{cantidad - current_balance:.4f}", inline=True)
            embed.set_footer(text=f"Compra más {crypto_symbol} con /crypto buy")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Calcular ganancias totales
        total_earnings = int(cantidad * current_price)
        
        # Calcular precio promedio de compra y ganancias
        invested = wallet.get('total_invested', 0)
        total_crypto = sum([
            wallet.get('btc_balance', 0.0),
            wallet.get('eth_balance', 0.0),
            wallet.get('dog_balance', 0.0)
        ]) + cantidad
        
        avg_buy_price = invested / total_crypto if total_crypto > 0 else current_price
        profit = total_earnings - (cantidad * avg_buy_price)
        profit_percent = (profit / (cantidad * avg_buy_price) * 100) if (cantidad * avg_buy_price) > 0 else 0
        
        # Realizar venta
        try:
            # Actualizar balance de monedas normales
            if not update_player_balance(str(interaction.user.id), total_earnings):
                raise Exception("Error actualizando balance de monedas")
            
            # Actualizar wallet de cripto
            if not update_crypto_balance(str(interaction.user.id), crypto_symbol, -cantidad, total_earnings):
                raise Exception("Error actualizando balance de cripto")
            
            # Obtener nuevos balances
            new_player_balance = get_player_balance(str(interaction.user.id))
            new_wallet = get_or_create_crypto_wallet(str(interaction.user.id))
            new_crypto_balance = new_wallet.get(crypto_column, 0.0) if new_wallet else 0.0
            
            # Crear embed mejorado
            embed_color = 0x00FF00 if profit_percent >= 0 else 0xFF0000
            profit_emoji = "📈" if profit_percent >= 0 else "📉"
            market_change_emoji = "📈" if market_change_percent >= 0 else "📉"
            
            embed = discord.Embed(
                title=f"{profit_emoji} VENTA EXITOSA | {config['emoji']} {config['name']}",
                description=f"Transacción completada exitosamente",
                color=embed_color
            )
            
            # Añadir thumbnail con icono de la criptomoneda
            embed.set_thumbnail(url=config["icon"])
            
            # Información de mercado
            embed.add_field(
                name="📊 Estado del Mercado",
                value=f"**Precio Actual:** {current_price:,} monedas\n"
                      f"**Cambio del Mercado:** {market_change_percent:+.2f}% {market_change_emoji}\n"
                      f"**Precio Original:** {original_price:,} monedas",
                inline=False
            )
            
            # Información de la transacción
            embed.add_field(
                name="📊 Detalles de la Venta",
                value=f"**Cantidad:** {cantidad:.4f} {crypto_symbol}\n"
                      f"**Precio Unitario:** {current_price:,} monedas\n"
                      f"**Total Obtenido:** {total_earnings:,} monedas",
                inline=False
            )
            
            # Estadísticas de ganancias
            embed.add_field(
                name="💰 Rendimiento Personal",
                value=f"**Ganancia/Pérdida:** {profit:+,.0f} monedas\n"
                      f"**Porcentaje:** {profit_percent:+.1f}%\n"
                      f"**Precio Promedio:** {avg_buy_price:,.0f} monedas",
                inline=False
            )
            
            # Balances actualizados
            embed.add_field(
                name="💳 Nuevos Balances",
                value=f"**Monedas:** {new_player_balance:,}\n"
                      f"**{crypto_symbol}:** {new_crypto_balance:.4f}",
                inline=False
            )
            
            # Timestamp y footer
            embed.timestamp = datetime.now()
            embed.set_footer(text=f"Transacción ID: {str(interaction.id)[:8]}", icon_url=interaction.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Actualizar leaderboard en segundo plano
            try:
                await update_global_leaderboard(interaction.client)
            except Exception as e:
                print(f"⚠️  Error al actualizar leaderboard después de venta: {e}")
            
        except Exception as e:
            print(f"❌ Error en venta: {e}")
            embed = discord.Embed(
                title="❌ Error en la Transacción",
                description="Ocurrió un error al procesar tu venta.",
                color=0xFF0000
            )
            embed.add_field(name="🔧 Solución", value="Intenta nuevamente en unos momentos.", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
