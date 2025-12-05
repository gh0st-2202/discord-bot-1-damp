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

def update_crypto_balance(discord_id, crypto, amount, total_cost=None):
    supabase = get_supabase_client()
    try:
        wallet = get_or_create_crypto_wallet(discord_id)
        if not wallet:
            return False
        
        crypto_column = f'{crypto.lower()}_balance'
        current_balance = wallet.get(crypto_column, 0.0)
        new_balance = current_balance + amount
        
        update_data = {crypto_column: new_balance}
        
        if total_cost is not None:
            if amount > 0:  # Compra
                current_invested = wallet.get('total_invested', 0)
                update_data['total_invested'] = int(current_invested + total_cost)
        
        supabase.table('crypto_wallets').update(update_data).eq('discord_id', discord_id).execute()
        return True
    except Exception as e:
        print(f"❌ Error al actualizar balance de cripto: {e}")
        return False

# ============ COMANDO MEJORADO ============
def setup_command(crypto_group, cog):
    @crypto_group.command(name="buy", description="Comprar criptomonedas")
    @app_commands.describe(
        moneda="Criptomoneda a comprar",
        cantidad="Cantidad a comprar"
    )
    @app_commands.choices(
        moneda=[
            app_commands.Choice(name="BitCord (BTC)", value="BTC"),
            app_commands.Choice(name="Etherium (ETH)", value="ETH"),
            app_commands.Choice(name="DoggoCoin (DOG)", value="DOG")
        ]
    )
    async def buy(interaction: discord.Interaction, moneda: str, cantidad: float):
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
        change_percent = crypto_data.get('change_percent', 0.0)
        original_price = crypto_data.get('original', current_price)
        
        wallet = get_or_create_crypto_wallet(str(interaction.user.id))
        player_balance = get_player_balance(str(interaction.user.id))
        
        if wallet is None:
            await interaction.followup.send("❌ Error al acceder a tu wallet", ephemeral=True)
            return
        
        if current_price <= 0:
            await interaction.followup.send("❌ Error: Precio inválido", ephemeral=True)
            return
        
        # Calcular costo total
        total_cost = int(cantidad * current_price)
        
        # Verificar fondos
        if player_balance < total_cost:
            embed = discord.Embed(
                title="❌ Fondos Insuficientes",
                description=f"No tienes suficientes monedas para esta compra.",
                color=0xFF0000
            )
            embed.add_field(name="💳 Saldo Actual", value=f"{player_balance:,} monedas", inline=True)
            embed.add_field(name="💰 Costo Total", value=f"{total_cost:,} monedas", inline=True)
            embed.add_field(name="📉 Faltante", value=f"{total_cost - player_balance:,} monedas", inline=True)
            embed.set_footer(text="Usa /work o /daily para ganar más monedas")
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Realizar compra
        try:
            # Actualizar balances
            if not update_player_balance(str(interaction.user.id), -total_cost):
                raise Exception("Error actualizando balance de monedas")
            
            if not update_crypto_balance(str(interaction.user.id), crypto_symbol, cantidad, total_cost):
                raise Exception("Error actualizando balance de cripto")
            
            # Obtener nuevo balance después de la compra
            new_wallet_balance = get_or_create_crypto_wallet(str(interaction.user.id))
            new_crypto_balance = new_wallet_balance.get(f'{crypto_symbol.lower()}_balance', 0.0) if new_wallet_balance else 0.0
            
            # Crear embed mejorado
            embed = discord.Embed(
                title=f"✅ COMPRA EXITOSA | {config['emoji']} {config['name']}",
                description=f"Transacción completada exitosamente",
                color=config["color"]
            )
            
            # Añadir thumbnail con icono de la criptomoneda
            embed.set_thumbnail(url=config["icon"])
            
            # Información de mercado
            change_emoji = "📈" if change_percent >= 0 else "📉"
            embed.add_field(
                name="📊 Estado del Mercado",
                value=f"**Precio Actual:** {current_price:,} monedas\n"
                      f"**Cambio:** {change_percent:+.2f}% {change_emoji}\n"
                      f"**Precio Original:** {original_price:,} monedas",
                inline=False
            )
            
            # Información de la transacción
            embed.add_field(
                name="📊 Detalles de la Compra",
                value=f"**Cantidad:** {cantidad:.4f} {crypto_symbol}\n"
                      f"**Precio Unitario:** {current_price:,} monedas\n"
                      f"**Costo Total:** {total_cost:,} monedas",
                inline=False
            )
            
            # Balances actualizados
            embed.add_field(
                name="💳 Nuevos Balances",
                value=f"**Monedas:** {player_balance - total_cost:,}\n"
                      f"**{crypto_symbol}:** {new_crypto_balance:.4f}",
                inline=False
            )
            
            # Timestamp y footer
            embed.timestamp = datetime.now()
            embed.set_footer(text=f"Transacción ID: {interaction.id[:8]}", icon_url=interaction.user.display_avatar.url)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Error en compra: {e}")
            embed = discord.Embed(
                title="❌ Error en la Transacción",
                description="Ocurrió un error al procesar tu compra.",
                color=0xFF0000
            )
            embed.add_field(name="🔧 Solución", value="Intenta nuevamente en unos momentos.", inline=False)
            await interaction.followup.send(embed=embed, ephemeral=True)
