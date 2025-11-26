import discord
from discord import app_commands
import asyncio
import random
import sqlite3

# Funciones de base de datos locales para evitar importaciones circulares
DB_FILE = "players.db"
INITIAL_BALANCE = 500

def get_player_local(discord_id, username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    player = c.fetchone()
    if not player:
        c.execute("INSERT INTO players (discord_id, username, balance) VALUES (?, ?, ?)",
                  (discord_id, username, INITIAL_BALANCE))
        conn.commit()
        c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
        player = c.fetchone()
    conn.close()
    return player

def update_balance_local(discord_id, amount):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (amount, discord_id))
    conn.commit()
    conn.close()

def get_leaderboard_local():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT username, balance FROM players ORDER BY balance DESC")
    data = c.fetchall()
    conn.close()
    return data

# Funciones globales locales
async def update_global_leaderboard_local(bot):
    CHANNEL_LEADERBOARD_ID = 1430215076769435800
    channel = bot.get_channel(CHANNEL_LEADERBOARD_ID)
    if not channel:
        print("❌ Canal de leaderboard no encontrado")
        return
    
    try:
        leaderboard = get_leaderboard_local()
        await channel.purge()
        
        embed = discord.Embed(title="🏆 TABLA DE LÍDERES GLOBAL", color=discord.Color.gold())
        
        for i, (name, balance) in enumerate(leaderboard[:10], start=1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            embed.add_field(
                name=f"{medal} {name}", 
                value=f"```{balance:,} monedas```", 
                inline=False
            )
        
        embed.set_footer(text="Actualizado automáticamente")
        await channel.send(embed=embed)
        print("✅ Leaderboard global actualizado")
        
    except Exception as e:
        print(f"❌ Error actualizando leaderboard: {e}")

async def update_global_trophy_wall_local(bot, winner=None, game_type="Blackjack"):
    CHANNEL_TROPHY_ID = 1430215324111736953
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

def setup_command(blackjack_group, cog):
    """Configura el comando play en el grupo blackjack"""
    
    @blackjack_group.command(name="crear", description="Inicia una partida de blackjack multijugador.")
    @app_commands.describe(apuesta_min="Cantidad mínima a apostar")
    async def play(interaction: discord.Interaction, apuesta_min: int):
        if apuesta_min <= 0:
            await interaction.response.send_message("❌ La apuesta mínima debe ser mayor a 0.", ephemeral=True)
            return
    
        CHANNEL_BET_ID = 1430216318933794927
        channel = cog.bot.get_channel(CHANNEL_BET_ID)
        if not channel:
            await interaction.response.send_message("❌ Canal de apuestas no encontrado.", ephemeral=True)
            return
    
        cog.current_bet_min = apuesta_min
        cog.player_bets.clear()
        
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
        
        players_data = cog.player_bets.copy()
        cog.current_bet_min = 0
        cog.player_bets.clear()
    
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
    
        # Importar funciones de blackjack del módulo padre
        from cog.juegos.blackjack import create_deck, draw_card, calculate_hand_value, format_hand, format_card, BlackjackButtons
        
        deck = create_deck()
        hands = {p: [draw_card(deck), draw_card(deck)] for p in players_data.keys()}
        dealer = [draw_card(deck), draw_card(deck)]
    
        # TURNOS CON INTERFAZ MEJORADA
        for player, bet_amount in players_data.items():
            player_data = get_player_local(str(player.id), player.name)
            
            if player_data[2] < bet_amount:
                embed = discord.Embed(
                    title="💸 Fondos Insuficientes",
                    description=f"{player.mention} no tiene suficiente dinero para apostar.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Apuesta", value=f"**{bet_amount:,}** monedas", inline=True)
                embed.add_field(name="Saldo", value=f"**{player_data[2]:,}** monedas", inline=True)
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
    
        # TURNO DEL DEALER MEJORADO - UN SOLO MENSAJE QUE SE EDITA
        dealer_embed = discord.Embed(
            title="🎩 TURNO DEL DEALER",
            color=discord.Color.dark_gray()
        )
        dealer_embed.add_field(name="Mano Inicial", value=f"```{format_hand(dealer)}```", inline=False)
        dealer_embed.add_field(name="Valor Actual", value=f"**{calculate_hand_value(dealer)} puntos**", inline=True)
        dealer_embed.add_field(name="Estado", value="🔄 El dealer está jugando...", inline=True)
        
        dealer_message = await channel.send(embed=dealer_embed)
    
        # Lógica del dealer - editar el mismo mensaje
        while calculate_hand_value(dealer) < 17:
            await asyncio.sleep(2)  # Pequeña pausa para dramatismo
            
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
    
        # DETERMINAR GANADORES CON INTERFAZ MEJORADA - SISTEMA MEJORADO
        winners = []
        results = []
    
        # Restar todas las apuestas primero
        for player, bet_amount in players_data.items():
            update_balance_local(str(player.id), -bet_amount)
    
        # Calcular el bote total (suma de todas las apuestas)
        total_bote = sum(players_data.values())
    
        # Identificar jugadores válidos (no se pasaron de 21)
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
                # Encontrar la mano más alta entre los válidos que superen al dealer
                max_value = max(valid_players.values())
                if max_value > dealer_value:
                    winners = [player for player, value in valid_players.items() if value == max_value]

        # SISTEMA MEJORADO: Ganadores recuperan su apuesta + reciben el bote completo
        if winners:
            # Distribuir el bote entre los ganadores
            prize_per_winner = total_bote // len(winners)
            extra_prize = total_bote % len(winners)
        
            for i, winner in enumerate(winners):
                apuesta_ganador = players_data[winner]
                # El ganador recupera su apuesta Y recibe su parte del bote
                premio_total = apuesta_ganador + prize_per_winner + (extra_prize if i == 0 else 0)
            
                # Actualizar balance: no restamos la apuesta, solo sumamos el premio
                update_balance_local(str(winner.id), premio_total)
            
                results.append({
                    "player": winner,
                    "premio": premio_total,
                    "apuesta": apuesta_ganador,
                    "mano": valid_players[winner],
                    "tipo": "ganador"
                })
        else:
            # Si no hay ganadores, el dealer se lleva todo (nadie recupera su apuesta)
            results.append({"tipo": "dealer_gana"})
    
        # Procesar perdedores
        for player, apuesta in players_data.items():
            player_value = calculate_hand_value(hands[player])
        
            if player not in winners:
                # Los perdedores pierden su apuesta (ya se restó al unirse)
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
    
        # EMBED DE RESULTADOS MEJORADO
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
                
                # Calcular ganancia neta (premio total - apuesta inicial)
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

        # EMBED INDIVIDUAL DE GANADORES MEJORADO
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
                
                player_data = get_player_local(str(winner.id), winner.name)
                
                embed.add_field(
                    name=f"🏅 {winner.display_name}",
                    value=(
                        f"**Apuesta recuperada:** {apuesta:,} monedas\n"
                        f"**Bote ganado:** {premio_total - apuesta:,} monedas\n"
                        f"**Premio total:** {premio_total:,} monedas\n"
                        f"**Ganancia neta:** +{ganancia_neta:,} monedas\n"
                        f"**Nuevo saldo:** {player_data[2]:,} monedas"
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
        await update_global_leaderboard_local(cog.bot)
        await update_global_trophy_wall_local(cog.bot, winners)
