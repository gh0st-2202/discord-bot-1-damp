import discord
from discord.ext import commands
from discord import app_commands
import time
import random
import asyncio
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicializar cliente de Supabase
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# Configuración
INITIAL_BALANCE = 500
CHANNEL_LEADERBOARD_ID = 1430215076769435800
CHANNEL_TROPHY_ID = 1430215324111736953
CHANNEL_BET_ID = 1430216318933794927

# Funciones de base de datos locales
async def get_player(discord_id, username):
    """Obtiene o crea un jugador en Supabase"""
    try:
        response = supabase.table("players").select("*").eq("discord_id", discord_id).execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        else:
            new_player = {
                "discord_id": discord_id,
                "username": username,
                "balance": INITIAL_BALANCE,
                "created_at": time.strftime('%Y-%m-%d %H:%M:%S')
            }
            response = supabase.table("players").insert(new_player).execute()
            return response.data[0] if response.data else None
    except Exception as e:
        print(f"Error en get_player: {e}")
        return None

async def update_balance(discord_id, amount):
    """Actualiza el balance de un jugador en Supabase"""
    try:
        response = supabase.table("players").select("balance").eq("discord_id", discord_id).execute()
        
        if response.data and len(response.data) > 0:
            current_balance = response.data[0]["balance"]
            new_balance = current_balance + amount
            
            supabase.table("players").update({"balance": new_balance}).eq("discord_id", discord_id).execute()
            return new_balance
        return None
    except Exception as e:
        print(f"Error en update_balance: {e}")
        return None

async def get_leaderboard(limit=10):
    """Obtiene el leaderboard desde Supabase"""
    try:
        response = supabase.table("players").select("username, balance").order("balance", desc=True).limit(limit).execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"Error en get_leaderboard: {e}")
        return []

async def update_global_leaderboard(bot):
    """Actualiza el leaderboard global en el canal especificado"""
    channel = bot.get_channel(CHANNEL_LEADERBOARD_ID)
    if not channel:
        print("❌ Canal de leaderboard no encontrado")
        return
    
    try:
        leaderboard = await get_leaderboard(10)
        await channel.purge()
        
        embed = discord.Embed(title="🏆 TABLA DE LÍDERES GLOBAL", color=discord.Color.gold())
        
        for i, player in enumerate(leaderboard[:10], start=1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(
                name=f"{medal} {player['username']}", 
                value=f"```{player['balance']:,} monedas```", 
                inline=False
            )
        
        embed.set_footer(text="Actualizado automáticamente")
        await channel.send(embed=embed)
        print("✅ Leaderboard global actualizado")
        
    except Exception as e:
        print(f"❌ Error actualizando leaderboard: {e}")

async def update_global_trophy_wall(bot, winner=None, game_type="Blackjack"):
    """Actualiza el muro de trofeos"""
    channel = bot.get_channel(CHANNEL_TROPHY_ID)
    if not channel:
        return
    
    try:
        await channel.purge()
        
        embed = discord.Embed(
            title="🎊 MURO DE LA FAMA",
            description=f"Últimos ganadores de {game_type}",
            color=discord.Color.green()
        )
        
        if winner:
            if isinstance(winner, list):
                for i, w in enumerate(winner[:5]):
                    embed.add_field(
                        name=f"🏅 {w.display_name}",
                        value=f"Ganó en la última partida de {game_type}",
                        inline=False
                    )
            else:
                embed.add_field(
                    name=f"🏅 {winner.display_name}",
                    value=f"Ganó en la última partida de {game_type}",
                    inline=False
                )
        else:
            embed.description = f"💀 Nadie ha ganado en la última partida de {game_type}"
        
        embed.set_footer(text="Actualizado después de cada partida")
        await channel.send(embed=embed)
        
    except Exception as e:
        print(f"❌ Error actualizando muro de trofeos: {e}")

# Funciones del juego Blackjack
def create_deck():
    """Crea un mazo de cartas"""
    suits = ['♠', '♥', '♦', '♣']
    values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    deck = [{'suit': suit, 'value': value} for suit in suits for value in values]
    random.shuffle(deck)
    return deck

def draw_card(deck):
    """Saca una carta del mazo"""
    return deck.pop()

def calculate_hand_value(hand):
    """Calcula el valor de una mano"""
    value = 0
    aces = 0
    
    for card in hand:
        if card['value'] in ['J', 'Q', 'K']:
            value += 10
        elif card['value'] == 'A':
            value += 11
            aces += 1
        else:
            value += int(card['value'])
    
    # Ajustar ases si es necesario
    while value > 21 and aces > 0:
        value -= 10
        aces -= 1
    
    return value

def format_card(card):
    """Formatea una carta para mostrar"""
    return f"{card['suit']}{card['value']}"

def format_hand(hand):
    """Formatea una mano de cartas para mostrar"""
    return " ".join([format_card(card) for card in hand])

class BlackjackButtons(discord.ui.View):
    """Vista de botones para el juego de Blackjack"""
    def __init__(self, player, hand, deck, bet, timeout=30):
        super().__init__(timeout=timeout)
        self.player = player
        self.hand = hand
        self.deck = deck
        self.bet = bet
        self.stand = False
        self.busted = False
        self.message = None

    @discord.ui.button(label="Pedir Carta", style=discord.ButtonStyle.primary, emoji="🃏")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            await interaction.response.send_message("No es tu turno!", ephemeral=True)
            return
        
        # Sacar carta
        card = draw_card(self.deck)
        self.hand.append(card)
        value = calculate_hand_value(self.hand)
        
        # Actualizar embed
        embed = interaction.message.embeds[0]
        embed.set_field_at(0, name="Tu Mano", value=f"```{format_hand(self.hand)}```", inline=False)
        embed.set_field_at(1, name="Valor Actual", value=f"**{value} puntos**", inline=True)
        
        if value > 21:
            embed.add_field(name="💥 Resultado", value="¡Te has pasado de 21!", inline=False)
            embed.color = discord.Color.red()
            self.busted = True
            await interaction.response.edit_message(embed=embed, view=None)
            self.stop()
        else:
            await interaction.response.edit_message(embed=embed)

    @discord.ui.button(label="Plantarse", style=discord.ButtonStyle.secondary, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            await interaction.response.send_message("No es tu turno!", ephemeral=True)
            return
        
        self.stand = True
        embed = interaction.message.embeds[0]
        embed.add_field(name="✅ Decisión", value="Te has plantado", inline=False)
        await interaction.response.edit_message(embed=embed, view=None)
        self.stop()

class BlackjackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_bet_min = 0
        self.player_bets = {}

    # Grupo de comandos de Blackjack
    blackjack = app_commands.Group(name="blackjack", description="Comandos para jugar al Blackjack")

    @blackjack.command(name="crear", description="Inicia una partida de blackjack multijugador.")
    @app_commands.describe(apuesta_min="Cantidad mínima a apostar")
    async def crear(self, interaction: discord.Interaction, apuesta_min: int):
        if apuesta_min <= 0:
            await interaction.response.send_message("❌ La apuesta mínima debe ser mayor a 0.", ephemeral=True)
            return
    
        channel = self.bot.get_channel(CHANNEL_BET_ID)
        if not channel:
            await interaction.response.send_message("❌ Canal de apuestas no encontrado.", ephemeral=True)
            return
    
        self.current_bet_min = apuesta_min
        self.player_bets.clear()
        
        # Embed de inicio de partida
        embed = discord.Embed(
            title="🎰 NUEVA PARTIDA DE BLACKJACK",
            description=f"¡Una nueva partida ha comenzado en {channel.mention}!",
            color=discord.Color.purple()
        )
        embed.add_field(name="💰 Apuesta Mínima", value=f"**{apuesta_min:,}** monedas", inline=True)
        embed.add_field(name="🏆 Premio", value="**¡GANADOR SE LLEVA TODO!**", inline=True)
        embed.add_field(name="⏰ Tiempo", value="**60 segundos** para unirse", inline=True)
        embed.set_footer(text="Usa /blackjack unirse [cantidad] para participar")
        
        await interaction.response.send_message(embed=embed)
        await asyncio.sleep(60)
        
        players_data = self.player_bets.copy()
        self.current_bet_min = 0
        self.player_bets.clear()
    
        if not players_data:
            embed = discord.Embed(
                title="⏹️ Partida Cancelada",
                description="No se unió nadie a la partida.",
                color=discord.Color.red()
            )
            await channel.send(embed=embed)
            return
    
        # Embed de inicio del juego
        total_bote = sum(players_data.values())
        embed = discord.Embed(
            title="🎲 COMIENZA EL JUEGO",
            description=f"**{len(players_data)} jugadores** participan en esta ronda",
            color=discord.Color.gold()
        )
        embed.add_field(name="💰 Bote Total", value=f"**{total_bote:,}** monedas", inline=True)
        embed.add_field(name="🎯 Objetivo", value="**Vencer al dealer**", inline=True)
        
        # Lista de jugadores y apuestas
        players_list = "\n".join([f"• {p.mention}: **{bet:,}** monedas" for p, bet in players_data.items()])
        embed.add_field(name="👥 Jugadores", value=players_list, inline=False)
        
        await channel.send(embed=embed)
    
        # Preparar el juego
        deck = create_deck()
        hands = {p: [draw_card(deck), draw_card(deck)] for p in players_data.keys()}
        dealer = [draw_card(deck), draw_card(deck)]
    
        # Turnos de los jugadores
        for player, bet_amount in players_data.items():
            player_data = await get_player(str(player.id), player.name)
            
            if player_data["balance"] < bet_amount:
                embed = discord.Embed(
                    title="💸 Fondos Insuficientes",
                    description=f"{player.mention} no tiene suficiente dinero para apostar.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Apuesta", value=f"**{bet_amount:,}** monedas", inline=True)
                embed.add_field(name="Saldo", value=f"**{player_data['balance']:,}** monedas", inline=True)
                await channel.send(embed=embed)
                continue

            # Crear embed para el turno del jugador
            embed = discord.Embed(
                title=f"🎴 Turno de {player.display_name}",
                color=discord.Color.blue()
            )
            embed.add_field(name="Tu Mano", value=f"```{format_hand(hands[player])}```", inline=False)
            embed.add_field(name="Valor Actual", value=f"**{calculate_hand_value(hands[player])} puntos**", inline=True)
            embed.add_field(name="Apuesta", value=f"**{bet_amount:,}** 💰", inline=True)
            embed.set_thumbnail(url=player.display_avatar.url)
            embed.set_footer(text="Tienes 30 segundos para decidir")

            # Crear vista con botones
            view = BlackjackButtons(player, hands[player].copy(), deck, bet_amount, timeout=30)
            message = await channel.send(embed=embed, view=view)
            view.message = message
        
            # Esperar a que el jugador termine su turno
            await view.wait()
            
            # Actualizar la mano con cualquier carta nueva
            hands[player] = view.hand
    
        # Turno del dealer
        dealer_embed = discord.Embed(
            title="🎩 TURNO DEL DEALER",
            color=discord.Color.dark_gray()
        )
        dealer_embed.add_field(name="Mano Inicial", value=f"```{format_hand(dealer)}```", inline=False)
        dealer_embed.add_field(name="Valor Actual", value=f"**{calculate_hand_value(dealer)} puntos**", inline=True)
        dealer_embed.add_field(name="Estado", value="🔄 El dealer está jugando...", inline=True)
        
        dealer_message = await channel.send(embed=dealer_embed)
    
        # Lógica del dealer
        while calculate_hand_value(dealer) < 17:
            await asyncio.sleep(2)
            
            card = draw_card(deck)
            dealer.append(card)
            dealer_value = calculate_hand_value(dealer)
            
            # Actualizar el embed existente
            dealer_embed.clear_fields()
            dealer_embed.add_field(name="Mano Actual", value=f"```{format_hand(dealer)}```", inline=False)
            dealer_embed.add_field(name="Valor Actual", value=f"**{dealer_value} puntos**", inline=True)
            dealer_embed.add_field(name="Última Carta", value=f"**{format_card(card)}**", inline=True)
            
            if dealer_value < 17:
                dealer_embed.set_field_at(2, name="Estado", value="🔄 El dealer pide otra carta...", inline=True)
            elif dealer_value >= 17:
                dealer_embed.set_field_at(2, name="Estado", value="✅ El dealer se planta", inline=True)
        
            await dealer_message.edit(embed=dealer_embed)
    
        dealer_value = calculate_hand_value(dealer)
        
        # Mensaje final del dealer
        dealer_embed.clear_fields()
        dealer_embed.add_field(name="Mano Final", value=f"```{format_hand(dealer)}```", inline=False)
        dealer_embed.add_field(name="Valor Final", value=f"**{dealer_value} puntos**", inline=True)
        
        if dealer_value > 21:
            dealer_embed.add_field(name="Resultado", value="💥 **¡El dealer se pasó de 21!**", inline=True)
            dealer_embed.color = discord.Color.green()
        else:
            dealer_embed.add_field(name="Resultado", value="🎯 **El dealer se planta**", inline=True)
            dealer_embed.color = discord.Color.dark_grey()
    
        await dealer_message.edit(embed=dealer_embed)
    
        # Determinar ganadores
        winners = []
        results = []
    
        # Restar todas las apuestas primero
        for player, bet_amount in players_data.items():
            await update_balance(str(player.id), -bet_amount)
    
        # Calcular el bote total
        total_bote = sum(players_data.values())
    
        # Identificar jugadores válidos
        valid_players = {}
        for player in players_data.keys():
            player_value = calculate_hand_value(hands[player])
            if player_value <= 21:
                valid_players[player] = player_value

        # Determinar ganadores
        if valid_players:
            if dealer_value > 21:
                # Dealer se pasó - todos los válidos ganan
                winners = list(valid_players.keys())
            else:
                # Encontrar la mano más alta
                max_value = max(valid_players.values())
                if max_value > dealer_value:
                    winners = [player for player, value in valid_players.items() if value == max_value]

        # Distribuir premios
        if winners:
            prize_per_winner = total_bote // len(winners)
            extra_prize = total_bote % len(winners)
        
            for i, winner in enumerate(winners):
                apuesta_ganador = players_data[winner]
                premio_total = apuesta_ganador + prize_per_winner + (extra_prize if i == 0 else 0)
            
                # Actualizar balance
                await update_balance(str(winner.id), premio_total)
            
                results.append({
                    "player": winner,
                    "premio": premio_total,
                    "apuesta": apuesta_ganador,
                    "mano": valid_players[winner],
                    "tipo": "ganador"
                })
        else:
            results.append({"tipo": "dealer_gana"})
    
        # Procesar perdedores
        for player, apuesta in players_data.items():
            player_value = calculate_hand_value(hands[player])
        
            if player not in winners:
                if player_value > 21:
                    results.append({
                        "player": player,
                        "apuesta": apuesta,
                        "mano": player_value,
                        "tipo": "se_paso"
                    })
                elif player_value <= dealer_value <= 21:
                    results.append({
                        "player": player,
                        "apuesta": apuesta,
                        "mano": player_value,
                        "tipo": "mano_menor"
                    })
                elif dealer_value > 21 and player_value <= 21:
                    results.append({
                        "player": player,
                        "apuesta": apuesta,
                        "mano": player_value,
                        "tipo": "no_maxima"
                    })
    
        # Embed de resultados finales
        embed = discord.Embed(
            title="🏁 RESULTADOS FINALES",
            color=discord.Color.purple()
        )
        embed.add_field(name="💰 Bote Total", value=f"**{total_bote:,}** monedas", inline=True)
        embed.add_field(name="🎯 Mano del Dealer", value=f"**{dealer_value} puntos**", inline=True)
        
        # Mostrar ganadores
        if winners:
            winners_text = []
            for i, result in enumerate([r for r in results if r["tipo"] == "ganador"]):
                w = result["player"]
                premio = result["premio"]
                apuesta = result["apuesta"]
                mano = result["mano"]
                
                ganancia_neta = premio - apuesta
                
                winners_text.append(
                    f"🎉 {w.mention} - **{mano} puntos**\n"
                    f"   Apuesta: {apuesta:,} → Premio: {premio:,}\n"
                    f"   Ganancia neta: **+{ganancia_neta:,}** monedas"
                )
            
            embed.add_field(name="🏆 GANADORES", value="\n\n".join(winners_text), inline=False)
        else:
            embed.add_field(name="🏆 GANADOR", value="💀 **El Dealer** se lleva todo el bote", inline=False)
        
        # Mostrar perdedores
        perdedores = [r for r in results if r["tipo"] in ["se_paso", "mano_menor", "no_maxima"]]
        if perdedores:
            perdedores_text = []
            for result in perdedores:
                p = result["player"]
                apuesta = result["apuesta"]
                mano = result["mano"]
                tipo = result["tipo"]
                
                if tipo == "se_paso":
                    razon = "Se pasó de 21"
                elif tipo == "mano_menor":
                    razon = "Mano menor al dealer"
                else:
                    razon = "No tuvo la mano más alta"
                
                perdedores_text.append(f"❌ {p.mention} - {mano} pts - {razon} - Pierde {apuesta:,}")
            
            embed.add_field(name="💀 PERDEDORES", value="\n".join(perdedores_text), inline=False)
        
        await channel.send(embed=embed)

        # Embed individual de ganadores
        if winners:
            embed = discord.Embed(
                title="🎊 ¡FELICITACIONES A LOS GANADORES!",
                color=discord.Color.gold()
            )
        
            for i, result in enumerate([r for r in results if r["tipo"] == "ganador"]):
                winner = result["player"]
                premio_total = result["premio"]
                apuesta = result["apuesta"]
                ganancia_neta = premio_total - apuesta
                
                player_data = await get_player(str(winner.id), winner.name)
                
                embed.add_field(
                    name=f"🏅 {winner.display_name}",
                    value=(
                        f"**Apuesta recuperada:** {apuesta:,} monedas\n"
                        f"**Bote ganado:** {premio_total - apuesta:,} monedas\n"
                        f"**Premio total:** {premio_total:,} monedas\n"
                        f"**Ganancia neta:** +{ganancia_neta:,} monedas\n"
                        f"**Nuevo saldo:** {player_data['balance']:,} monedas"
                    ),
                    inline=False
                )
                embed.set_thumbnail(url=winner.display_avatar.url)
        else:
            embed = discord.Embed(
                title="😔 Nadie Ganó Esta Partida",
                description=(
                    f"💀 El dealer se llevó el bote de **{total_bote:,}** monedas\n\n"
                ),
                color=discord.Color.red()
            )
    
        await channel.send(embed=embed)
        
        # Actualizar leaderboard y muro de trofeos
        try:
            await update_global_leaderboard(self.bot)
            await update_global_trophy_wall(self.bot, winners)
        except Exception as e:
            print(f"❌ Error actualizando leaderboard/trophy después de blackjack: {e}")

    @blackjack.command(name="unirse", description="Únete a la partida de Blackjack actual.")
    @app_commands.describe(apuesta="Cantidad a apostar")
    async def unirse(self, interaction: discord.Interaction, apuesta: int):
        if self.current_bet_min == 0:
            await interaction.response.send_message("❌ No hay ninguna partida activa. Usa `/blackjack crear` para iniciar una.", ephemeral=True)
            return
    
        if interaction.user in self.player_bets:
            await interaction.response.send_message("❌ Ya estás en la partida.", ephemeral=True)
            return
    
        if apuesta < self.current_bet_min:
            await interaction.response.send_message(f"❌ La apuesta mínima es de {self.current_bet_min:,} monedas.", ephemeral=True)
            return
    
        player_data = await get_player(str(interaction.user.id), interaction.user.name)
        if player_data["balance"] < apuesta:
            await interaction.response.send_message(f"❌ No tienes suficiente dinero. Tu saldo: {player_data['balance']:,} monedas.", ephemeral=True)
            return
    
        self.player_bets[interaction.user] = apuesta
    
        embed = discord.Embed(
            title="✅ Jugador Unido",
            description=f"{interaction.user.mention} se ha unido a la partida",
            color=discord.Color.green()
        )
        embed.add_field(name="Apuesta", value=f"**{apuesta:,}** monedas", inline=True)
        embed.add_field(name="Saldo Restante", value=f"**{player_data['balance'] - apuesta:,}** monedas", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
    
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(BlackjackCog(bot))
