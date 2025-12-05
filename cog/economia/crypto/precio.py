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

# ============ COMANDO PRECIO MEJORADO ============
def setup_command(crypto_group, cog):
    @crypto_group.command(name="precio", description="Ver precios actuales de criptomonedas con cambios porcentuales")
    @app_commands.describe(
        moneda="Criptomoneda específica (opcional)"
    )
    @app_commands.choices(
        moneda=[
            app_commands.Choice(name="BitCord (BTC)", value="BTC"),
            app_commands.Choice(name="Etherium (ETH)", value="ETH"),
            app_commands.Choice(name="DoggoCoin (DOG)", value="DOG")
        ]
    )
    async def precio(interaction: discord.Interaction, moneda: str):
        """Muestra el precio actual de criptomonedas con porcentaje de cambio"""
        await interaction.response.defer()
        
        # Obtener precios con cambios porcentuales
        prices_data = get_current_prices_with_change()
        
        # Configuraciones de criptomonedas
        configs = {
            "BTC": {
                "name": "BitCord", 
                "emoji": "₿", 
                "color": 0xF7931A,
                "icon": "https://cryptologos.cc/logos/bitcoin-btc-logo.png",
                "description": "La criptomoneda líder del mercado"
            },
            "ETH": {
                "name": "Etherium", 
                "emoji": "Ξ", 
                "color": 0x627EEA,
                "icon": "https://cryptologos.cc/logos/ethereum-eth-logo.png",
                "description": "Plataforma para contratos inteligentes"
            },
            "DOG": {
                "name": "DoggoCoin", 
                "emoji": "🐕", 
                "color": 0xF2A900,
                "icon": "https://cryptologos.cc/logos/dogecoin-doge-logo.png",
                "description": "La criptomoneda más divertida"
            }
        }
        
        # Si se especifica una moneda o mostrar_todas es False
        if True:
            crypto_symbol = moneda.upper()
            
            if crypto_symbol not in configs:
                await interaction.followup.send("❌ Criptomoneda no válida", ephemeral=True)
                return
            
            config = configs[crypto_symbol]
            crypto_data = prices_data.get(crypto_symbol, {})
            current_price = crypto_data.get('price', 0)
            change_percent = crypto_data.get('change_percent', 0.0)
            original_price = crypto_data.get('original', current_price)
            
            # Calcular cambio absoluto
            change_absolute = current_price - original_price
            
            # Crear embed detallado para una criptomoneda
            embed = discord.Embed(
                title=f"{config['emoji']} {config['name']} ({crypto_symbol})",
                description=config['description'],
                color=config["color"]
            )
            
            # Añadir thumbnail con icono
            embed.set_thumbnail(url=config["icon"])
            
            # Precio actual con formato atractivo
            change_emoji = "📈" if change_percent >= 0 else "📉"
            change_color = "🟢" if change_percent > 0 else "🔴" if change_percent < 0 else "⚪"
            
            price_display = f"```diff\n"
            if change_absolute >= 0:
                price_display += f"+ {current_price:,} monedas\n"
            else:
                price_display += f"- {current_price:,} monedas\n"
            price_display += f"```"
            
            embed.add_field(
                name="💰 PRECIO ACTUAL",
                value=price_display,
                inline=False
            )
            
            # Información de cambio
            embed.add_field(
                name="📊 CAMBIO PORCENTUAL",
                value=f"{change_color} **{change_percent:+.2f}%** {change_emoji}\n"
                      f"**Cambio Absoluto:** {change_absolute:+,.0f} monedas\n"
                      f"**Precio Original:** {original_price:,} monedas",
                inline=False
            )
            
            # Gráfico ASCII simple basado en el cambio
            bar_length = 20
            if abs(change_percent) > 100:
                filled = bar_length
            else:
                filled = min(bar_length, int(abs(change_percent) / 5))
            
            if change_percent >= 0:
                chart = "↗️ " + "█" * filled + "░" * (bar_length - filled)
            elif change_percent < 0:
                chart = "↘️ " + "░" * (bar_length - filled) + "█" * filled
            else:
                chart = "➡️ " + "─" * bar_length
            
            embed.add_field(
                name="📈 TENDENCIA VISUAL",
                value=f"```\n{chart}\n```",
                inline=False
            )
            
            # Recomendación basada en el cambio
            recommendation = ""
            if change_percent > 10:
                recommendation = "🔥 **Oportunidad de venta** - Los precios están muy altos"
            elif change_percent > 5:
                recommendation = "📈 **Tendencia alcista** - Considera comprar"
            elif change_percent < -10:
                recommendation = "💎 **Oportunidad de compra** - Los precios están muy bajos"
            elif change_percent < -5:
                recommendation = "📉 **Tendencia bajista** - Considera vender"
            else:
                recommendation = "⚖️ **Mercado estable** - Buen momento para diversificar"
            
            embed.add_field(
                name="💡 RECOMENDACIÓN",
                value=recommendation,
                inline=False
            )
            
            # Información técnica
            embed.add_field(
                name="ℹ️ INFORMACIÓN TÉCNICA",
                value=f"**Símbolo:** {crypto_symbol}\n"
                      f"**Emoji:** {config['emoji']}\n"
                      f"**Actualizado:** Ahora\n"
                      f"**Siguiente actualización:** En 5 minutos",
                inline=False
            )
            
            embed.set_footer(text="Usa /crypto buy para comprar o /crypto sell para vender")
            
            await interaction.followup.send(embed=embed)
            
        else:
            # Mostrar todas las criptomonedas
            embed = discord.Embed(
                title="📊 MERCADO DE CRIPTOMONEDAS - RESUMEN",
                description="Precios actuales y cambios porcentuales",
                color=0x5865F2,
                timestamp=datetime.now()
            )
            
            # Añadir banner o imagen
            embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1828/1828843.png")
            
            # Calcular resumen del mercado
            crypto_data_list = []
            total_market_cap = 0
            best_performer = None
            worst_performer = None
            
            for symbol, config in configs.items():
                crypto_data = prices_data.get(symbol, {})
                current_price = crypto_data.get('price', 0)
                change_percent = crypto_data.get('change_percent', 0.0)
                original_price = crypto_data.get('original', current_price)
                
                # Simular capitalización de mercado
                market_cap = current_price * 1000000
                total_market_cap += market_cap
                
                crypto_info = {
                    "symbol": symbol,
                    "price": current_price,
                    "change_percent": change_percent,
                    "original": original_price,
                    "market_cap": market_cap,
                    "config": config
                }
                crypto_data_list.append(crypto_info)
                
                # Actualizar mejor/peor rendimiento
                if best_performer is None or change_percent > best_performer["change_percent"]:
                    best_performer = {"symbol": symbol, "change": change_percent, "config": config}
                if worst_performer is None or change_percent < worst_performer["change_percent"]:
                    worst_performer = {"symbol": symbol, "change": change_percent, "config": config}
            
            # Ordenar por capitalización de mercado
            crypto_data_list.sort(key=lambda x: x["market_cap"], reverse=True)
            
            # Añadir cada criptomoneda al embed
            for data in crypto_data_list:
                symbol = data["symbol"]
                config = data["config"]
                change_percent = data["change_percent"]
                change_absolute = data["price"] - data["original"]
                
                change_emoji = "🟢 📈" if change_percent > 0 else "🔴 📉" if change_percent < 0 else "⚪ ➡️"
                change_text = f"{change_percent:+.2f}% ({change_absolute:+,.0f})"
                
                embed.add_field(
                    name=f"{config['emoji']} {config['name']} ({symbol})",
                    value=f"**Precio:** {data['price']:,} monedas\n"
                          f"**Cambio:** {change_text} {change_emoji}\n"
                          f"**Cap. Mercado:** {data['market_cap']:,.0f}",
                    inline=True
                )
            
            # Resumen del mercado
            market_summary = []
            if best_performer and best_performer["change"] > 0:
                market_summary.append(f"🏆 **Mejor rendimiento:** {best_performer['config']['emoji']} {best_performer['symbol']} (+{best_performer['change']:.2f}%)")
            if worst_performer and worst_performer["change"] < 0:
                market_summary.append(f"📉 **Peor rendimiento:** {worst_performer['config']['emoji']} {worst_performer['symbol']} ({worst_performer['change']:.2f}%)")
            
            embed.add_field(
                name="📈 RESUMEN DEL MERCADO",
                value=f"**💰 Capitalización Total:** {total_market_cap:,.0f}\n"
                      f"**📊 Criptomonedas:** 3\n"
                      f"**⏰ Última actualización:** Ahora\n"
                      f"**🔄 Siguiente actualización:** 5 minutos\n\n"
                      + "\n".join(market_summary),
                inline=False
            )
            
            # Gráfico de tendencias
            trends = []
            for data in crypto_data_list:
                trend = "↗️" if data["change_percent"] > 0 else "↘️" if data["change_percent"] < 0 else "➡️"
                color = "🟢" if data["change_percent"] > 0 else "🔴" if data["change_percent"] < 0 else "⚪"
                trends.append(f"{data['config']['emoji']} {color}{trend}")
            
            embed.add_field(
                name="🎯 TENDENCIAS ACTUALES",
                value=" ".join(trends),
                inline=False
            )
            
            # Recomendación general
            if best_performer and best_performer["change"] > 5:
                embed.add_field(
                    name="💡 RECOMENDACIÓN DEL DÍA",
                    value=f"Considera invertir en **{best_performer['config']['name']}** ({best_performer['config']['emoji']}) ya que muestra una tendencia alcista fuerte (+{best_performer['change']:.1f}%)",
                    inline=False
                )
            
            embed.set_footer(
                text="💡 Tip: Usa /crypto precio [moneda] para ver detalles específicos",
                icon_url=interaction.user.display_avatar.url
            )
            
            await interaction.followup.send(embed=embed)
