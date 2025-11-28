import discord
from discord import app_commands
import sqlite3
import time
import random
from typing import Optional

# Configuración del sistema de robos
ROB_SUCCESS_RATE = 0.40  # Aumentado a 40% de probabilidad de éxito
ROB_COOLDOWN = 1800  # 30 minutos en segundos

# Porcentajes de robo según número de cifras
ROB_PERCENTAGES = {
    1: 0.70,  # 1 cifra: 70%
    2: 0.60,  # 2 cifras: 60%
    3: 0.50,  # 3 cifras: 50%
    4: 0.40,  # 4 cifras: 40%
    5: 0.30,  # 5 cifras: 30%
    6: 0.20,  # 6 cifras: 20%
    7: 0.10   # 7+ cifras: 10%
}

# Porcentaje de penalización cuando falla el robo (reducido para hacerlo rentable)
ROB_PENALTY_PERCENT = 0.25  # 25% del monto intentado de robo

def get_player_local(discord_id, username):
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
    player = c.fetchone()
    if not player:
        c.execute("INSERT INTO players (discord_id, username, balance) VALUES (?, ?, ?)",
                  (discord_id, username, 500))
        conn.commit()
        c.execute("SELECT * FROM players WHERE discord_id = ?", (discord_id,))
        player = c.fetchone()
    conn.close()
    return player

def update_balance_local(discord_id, amount):
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    c.execute("UPDATE players SET balance = balance + ? WHERE discord_id = ?", (amount, discord_id))
    conn.commit()
    conn.close()

def get_rob_cooldown(discord_id):
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    
    # Verificar si existe la columna last_rob
    c.execute("PRAGMA table_info(players)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'last_rob' not in columns:
        # Agregar la columna si no existe
        c.execute("ALTER TABLE players ADD COLUMN last_rob INTEGER DEFAULT 0")
        conn.commit()
    
    c.execute("SELECT last_rob FROM players WHERE discord_id = ?", (discord_id,))
    result = c.fetchone()
    last_rob = result[0] if result else 0
    conn.close()
    
    return last_rob

def update_rob_cooldown(discord_id):
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    current_time = int(time.time())
    c.execute("UPDATE players SET last_rob = ? WHERE discord_id = ?", (current_time, discord_id))
    conn.commit()
    conn.close()

def get_digit_count(amount):
    """Calcula el número de cifras de una cantidad"""
    return len(str(abs(amount)))

def get_rob_percentage(amount):
    """Obtiene el porcentaje de robo según el número de cifras"""
    digits = get_digit_count(amount)
    
    # Para 7 o más cifras, usar 10%
    if digits >= 7:
        return ROB_PERCENTAGES[7]
    
    return ROB_PERCENTAGES.get(digits, 0.10)

def attempt_robbery(robber_id, victim_id, robber_username, victim_username):
    """Intenta realizar un robo y retorna los resultados"""
    conn = sqlite3.connect("players.db")
    c = conn.cursor()
    
    # Obtener balances actuales
    robber_data = get_player_local(robber_id, robber_username)
    victim_data = get_player_local(victim_id, victim_username)
    
    robber_balance = robber_data[2]
    victim_balance = victim_data[2]
    
    # Verificar que el ladrón tenga al menos 0 monedas
    if robber_balance < 0:
        conn.close()
        return "insufficient_funds", 0, 0, 0, 0
    
    # Verificar que la víctima tenga al menos 1 moneda
    if victim_balance < 1:
        conn.close()
        return "victim_poor", 0, 0, 0, 0
    
    # Determinar porcentaje de robo según cifras de la víctima
    rob_percentage = get_rob_percentage(victim_balance)
    attempted_rob_amount = int(victim_balance * rob_percentage)
    
    # Asegurar que se robe al menos 1 moneda
    attempted_rob_amount = max(1, attempted_rob_amount)
    
    # Verificar que no se robe más de lo que tiene la víctima
    actual_rob_amount = min(attempted_rob_amount, victim_balance)
    
    # Probabilidad de éxito
    success = random.random() <= ROB_SUCCESS_RATE
    
    if success:
        # Robo exitoso: transferir de víctima a ladrón
        update_balance_local(victim_id, -actual_rob_amount)
        update_balance_local(robber_id, actual_rob_amount)
        conn.close()
        return "success", actual_rob_amount, rob_percentage, 0, attempted_rob_amount
    else:
        # Robo fallido: penalización del ladrón a la víctima
        # La penalización es un porcentaje del monto que intentó robar
        penalty_amount = int(attempted_rob_amount * ROB_PENALTY_PERCENT)
        
        # Asegurar penalización mínima de 1 moneda
        penalty_amount = max(1, penalty_amount)
        
        # Limitar la penalización máxima al 50% del balance actual del ladrón
        # Esto evita que un robo fallido sea catastrófico
        max_penalty = max(1, int(robber_balance * 0.5))
        penalty_amount = min(penalty_amount, max_penalty)
        
        # Aplicar penalización (puede dejar balance negativo, pero limitado)
        update_balance_local(robber_id, -penalty_amount)
        update_balance_local(victim_id, penalty_amount)
        conn.close()
        return "failed", 0, rob_percentage, penalty_amount, attempted_rob_amount

def setup_command(economy_group, cog):
    """Configura el comando robar en el grupo economy"""
    
    @economy_group.command(name="robar", description="Intenta robar monedas a otro usuario (riesgo moderado)")
    @app_commands.describe(usuario="El usuario al que quieres robar")
    async def robar(interaction: discord.Interaction, usuario: discord.User):
        robber_id = str(interaction.user.id)
        robber_username = interaction.user.name
        victim_id = str(usuario.id)
        victim_username = usuario.name
        
        # No permitir robarse a sí mismo
        if robber_id == victim_id:
            embed = discord.Embed(
                title="❌ Robo Fallido",
                description="No puedes robarte a ti mismo!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Verificar cooldown
        last_rob = get_rob_cooldown(robber_id)
        current_time = int(time.time())
        time_since_last_rob = current_time - last_rob
        
        if time_since_last_rob < ROB_COOLDOWN:
            remaining_time = ROB_COOLDOWN - time_since_last_rob
            minutes = remaining_time // 60
            seconds = remaining_time % 60
            
            embed = discord.Embed(
                title="⏰ Enfriamiento Activo",
                description=f"Debes esperar {minutes}m {seconds}s antes de intentar otro robo.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Intentar el robo
        result, amount, percentage, penalty, attempted_amount = attempt_robbery(
            robber_id, victim_id, robber_username, victim_username
        )
        
        # Solo actualizar el cooldown si el robo se intentó realmente
        # (no cuando hay fondos insuficientes o víctima pobre)
        if result not in ["insufficient_funds", "victim_poor"]:
            update_rob_cooldown(robber_id)
        
        # Obtener el nuevo balance del ladrón después del robo
        robber_new_balance = get_player_local(robber_id, robber_username)[2]
        
        if result == "insufficient_funds":
            embed = discord.Embed(
                title="💸 Fondos Insuficientes",
                description="No puedes robar mientras tengas un balance negativo.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        elif result == "victim_poor":
            embed = discord.Embed(
                title="🎯 Víctima Pobre",
                description=f"{usuario.mention} no tiene suficientes monedas para robar.",
                color=discord.Color.orange()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        elif result == "success":
            # Mensajes divertidos para robos exitosos
            success_messages = [
                "¡Un robo limpio y profesional!",
                "¡Le has aliviado la cartera sin que se diera cuenta!",
                "¡Operación exitosa! El botín es tuyo.",
                "¡Como un fantasma en la noche, tomaste lo que querías!",
                "¡Robo magistral! Esa persona ni se enteró."
            ]
            
            embed = discord.Embed(
                title="🎊 ¡Robo Exitoso!",
                description=f"Has robado {amount:,} monedas de {usuario.mention}\n\n*{random.choice(success_messages)}*",
                color=discord.Color.green()
            )
            embed.add_field(
                name="📊 Detalles",
                value=f"• Porcentaje robado: {percentage*100:.0f}%\n• Botín: {amount:,} monedas\n• Nuevo balance: {robber_new_balance:,} monedas",
                inline=False
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed)
        
        elif result == "failed":
            # Mensajes divertidos para robos fallidos
            fail_messages = [
                "¡Casi lo logras! Pero te atraparon.",
                "¡Plan perfecto, ejecución desastrosa!",
                "¡La víctima estaba más alerta de lo que pensabas!",
                "¡Mal día para ser ladrón!",
                "¡Mejor suerte la próxima vez, caco!"
            ]
            
            embed = discord.Embed(
                title="🚨 ¡Robo Fallido!",
                description=f"El robo ha salido mal y has sido multado.\n\n*{random.choice(fail_messages)}*",
                color=discord.Color.red()
            )
            embed.add_field(
                name="💔 Penalización",
                value=f"• Has pagado {penalty:,} monedas a {usuario.mention}\n• Porcentaje intentado: {percentage*100:.0f}%\n• Monto intentado: {attempted_amount:,} monedas\n• **Nuevo balance: {robber_new_balance:,} monedas**",
                inline=False
            )
            
            # Mostrar advertencia si quedó en deuda
            if robber_new_balance < 0:
                embed.add_field(
                    name="⚠️ ¡ALERTA DE DEUDA!",
                    value=f"Ahora tienes una deuda de {abs(robber_new_balance):,} monedas. ¡Ten cuidado con tus próximos robos!",
                    inline=False
                )
            elif robber_new_balance < 50:
                embed.add_field(
                    name="💡 Consejo",
                    value="¡Estás jugando con fuego! Considera acumular más monedas antes de seguir robando.",
                    inline=False
                )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed)

    # Añadir un comando de estadísticas de robo para que los jugadores vean que es rentable
    @economy_group.command(name="estadisticas_robo", description="Muestra las estadísticas y expectativas del sistema de robos")
    async def estadisticas_robo(interaction: discord.Interaction):
        embed = discord.Embed(
            title="📈 Estadísticas del Sistema de Robos",
            description="¿Vale la pena robar? ¡Vamos a hacer cálculos!",
            color=discord.Color.blue()
        )
        
        # Ejemplo de cálculo de expectativa
        ejemplo_victima = 1000
        porcentaje_ejemplo = get_rob_percentage(ejemplo_victima)
        monto_intentado = int(ejemplo_victima * porcentaje_ejemplo)
        ganancia_esperada_exito = monto_intentado
        perdida_esperada_fracaso = int(monto_intentado * ROB_PENALTY_PERCENT)
        
        expectativa = (ROB_SUCCESS_RATE * ganancia_esperada_exito) - ((1 - ROB_SUCCESS_RATE) * perdida_esperada_fracaso)
        
        embed.add_field(
            name="⚖️ Expectativa Matemática",
            value=f"Con una víctima de {ejemplo_victima:,} monedas:\n"
                  f"• Probabilidad de éxito: {ROB_SUCCESS_RATE*100:.0f}%\n"
                  f"• Porcentaje de robo: {porcentaje_ejemplo*100:.0f}%\n"
                  f"• Ganancia si éxito: +{ganancia_esperada_exito:,}\n"
                  f"• Pérdida si fallo: -{perdida_esperada_fracaso:,}\n"
                  f"• **Expectativa por robo: +{expectativa:.0f} monedas**",
            inline=False
        )
        
        embed.add_field(
            name="📊 Configuración Actual",
            value=f"• Probabilidad de éxito: {ROB_SUCCESS_RATE*100:.0f}%\n"
                  f"• Penalización por fallo: {ROB_PENALTY_PERCENT*100:.0f}% del monto intentado\n"
                  f"• Enfriamiento: {ROB_COOLDOWN//60} minutos\n"
                  f"• Mínimo para robar: 0 monedas (no se permite balance negativo)",
            inline=False
        )
        
        embed.add_field(
            name="💡 Estrategia",
            value="¡En promedio, robar es ligeramente rentable! "
                  "Los robos a usuarios con más dinero tienen mayor riesgo pero también mayor recompensa. "
                  "¡Usa el comando con sabiduría!",
            inline=False
        )
        
        embed.set_footer(text="¡La suerte favorece a los audaces... pero no a los imprudentes!")
        await interaction.response.send_message(embed=embed)
