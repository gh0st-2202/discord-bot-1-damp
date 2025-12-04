import discord
from discord import app_commands
import os
from datetime import datetime
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
                'total_invested': 0,
                'total_withdrawn': 0
            }
            
            supabase.table('crypto_wallets').insert(wallet_data).execute()
            
            response = supabase.table('crypto_wallets').select('*').eq('discord_id', discord_id).execute()
            return response.data[0] if response.data else None
            
    except Exception as e:
        print(f"❌ Error al obtener/crear wallet: {e}")
        return None

def can_trade(discord_id, crypto):
    wallet = get_or_create_crypto_wallet(discord_id)
    if not wallet:
        return True
    
    last_trade_column = f'last_{crypto.lower()}_trade'
    last_trade = wallet.get(last_trade_column)
    
    if not last_trade:
        return True
    
    try:
        last_trade_time = datetime.fromisoformat(last_trade.replace('Z', '+00:00'))
        now = datetime.now().astimezone()
        hours_passed = (now - last_trade_time).total_seconds() / 3600
        
        return hours_passed >= 1
    except:
        return True

def update_last_trade(discord_id, crypto):
    supabase = get_supabase_client()
    try:
        last_trade_column = f'last_{crypto.lower()}_trade'
        supabase.table('crypto_wallets').update({
            last_trade_column: datetime.now().isoformat()
        }).eq('discord_id', discord_id).execute()
    except Exception as e:
        print(f"❌ Error al actualizar último trade: {e}")

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
                # Convertir a ENTERO
                update_data['total_invested'] = int(current_invested + total_cost)
            else:  # Venta (amount negativo)
                current_withdrawn = wallet.get('total_withdrawn', 0)
                update_data['total_withdrawn'] = int(current_withdrawn + abs(total_cost))
        
        supabase.table('crypto_wallets').update(update_data).eq('discord_id', discord_id).execute()
        return True
    except Exception as e:
        print(f"❌ Error al actualizar balance de cripto: {e}")
        return False

# ============ COMANDO ============
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
        
        # Colores para los embeds
        colors = {
            "BTC": 0xF7931A,
            "ETH": 0x627EEA,
            "DOG": 0xF2A900
        }
        
        if crypto_symbol not in ["BTC", "ETH", "DOG"]:
            await interaction.followup.send("❌ Criptomoneda no válida", ephemeral=True)
            return
        
        # Verificar cooldown
        if not can_trade(str(interaction.user.id), crypto_symbol):
            await interaction.followup.send(
                f"⏰ Debes esperar 1 hora entre transacciones de {crypto_symbol}",
                ephemeral=True
            )
            return
        
        # Obtener precios y wallet
        current_prices = get_current_prices()
        current_price = current_prices.get(crypto_symbol, 0)
        wallet = get_or_create_crypto_wallet(str(interaction.user.id))
        player_balance = get_player_balance(str(interaction.user.id))
        
        if wallet is None:
            await interaction.followup.send("❌ Error al acceder a tu wallet", ephemeral=True)
            return
        
        if current_price <= 0:
            await interaction.followup.send("❌ Error: Precio inválido", ephemeral=True)
            return
        
        # Calcular costo total (cantidad * precio entero)
        total_cost = int(cantidad * current_price)
        
        # Verificar fondos
        if player_balance < total_cost:
            await interaction.followup.send(
                f"❌ No tienes suficientes monedas. Necesitas {total_cost:,}, tienes {player_balance:,}",
                ephemeral=True
            )
            return
        
        # Realizar compra
        try:
            # Actualizar balances
            if not update_player_balance(str(interaction.user.id), -total_cost):
                raise Exception("Error actualizando balance de monedas")
            
            if not update_crypto_balance(str(interaction.user.id), crypto_symbol, cantidad, total_cost):
                raise Exception("Error actualizando balance de cripto")
            
            update_last_trade(str(interaction.user.id), crypto_symbol)
            
            # Crear embed de respuesta
            embed = discord.Embed(
                title="✅ Compra Exitosa",
                description=f"Has comprado **{cantidad:.4f} {crypto_symbol}**",
                color=colors.get(crypto_symbol, 0x00FF00)
            )
            
            embed.add_field(
                name="💸 Precio Unitario",
                value=f"{current_price:,} monedas",
                inline=True
            )
            
            embed.add_field(
                name="💰 Costo Total",
                value=f"{total_cost:,} monedas",
                inline=True
            )
            
            embed.add_field(
                name="💳 Nuevo Balance",
                value=f"{player_balance - total_cost:,} monedas",
                inline=True
            )
            
            embed.set_footer(text="Puedes vender en 1 hora")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            print(f"❌ Error en compra: {e}")
            await interaction.followup.send(
                "❌ Error al procesar la compra. Intenta nuevamente.",
                ephemeral=True
            )
