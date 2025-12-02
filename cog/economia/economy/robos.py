import discord
from discord import app_commands
import time
import random
from typing import Optional
import sys
import os

# Agregar el directorio padre al path para importar desde economy.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar desde el módulo principal
from economy import get_player, update_balance, update_player

# Configuración del sistema de robos
ROB_SUCCESS_RATE = 0.40
ROB_COOLDOWN = 1800
ROB_PENALTY_PERCENT = 0.25

ROB_PERCENTAGES = {
    1: 0.70,
    2: 0.60,
    3: 0.50,
    4: 0.40,
    5: 0.30,
    6: 0.20,
    7: 0.10
}

def get_digit_count(amount):
    return len(str(abs(amount)))

def get_rob_percentage(amount):
    digits = get_digit_count(amount)
    if digits >= 7:
        return ROB_PERCENTAGES[7]
    return ROB_PERCENTAGES.get(digits, 0.10)

async def get_rob_cooldown(discord_id):
    """Obtiene el tiempo del último robo desde Supabase"""
    try:
        player = await get_player(discord_id, "")
        return player.get("last_rob", 0) if player else 0
    except Exception as e:
        print(f"Error en get_rob_cooldown: {e}")
        return 0

async def update_rob_cooldown(discord_id):
    """Actualiza el cooldown del robo en Supabase"""
    try:
        await update_player(discord_id, {"last_rob": int(time.time())})
        return True
    except Exception as e:
        print(f"Error en update_rob_cooldown: {e}")
        return False

async def attempt_robbery(robber_id, victim_id, robber_username, victim_username):
    """Intenta realizar un robo usando Supabase"""
    try:
        # Obtener jugadores
        robber_data = await get_player(robber_id, robber_username)
        victim_data = await get_player(victim_id, victim_username)
        
        if not robber_data or not victim_data:
            return "error", 0, 0, 0, 0
        
        robber_balance = robber_data["balance"]
        victim_balance = victim_data["balance"]
        
        if robber_balance < 0:
            return "insufficient_funds", 0, 0, 0, 0
        
        if victim_balance < 1:
            return "victim_poor", 0, 0, 0, 0
        
        # Determinar porcentaje de robo
        rob_percentage = get_rob_percentage(victim_balance)
        attempted_rob_amount = int(victim_balance * rob_percentage)
        attempted_rob_amount = max(1, attempted_rob_amount)
        actual_rob_amount = min(attempted_rob_amount, victim_balance)
        
        # Probabilidad de éxito
        success = random.random() <= ROB_SUCCESS_RATE
        
        if success:
            # Robo exitoso
            await update_balance(victim_id, -actual_rob_amount)
            await update_balance(robber_id, actual_rob_amount)
            return "success", actual_rob_amount, rob_percentage, 0, attempted_rob_amount
        else:
            # Robo fallido
            penalty_amount = int(attempted_rob_amount * ROB_PENALTY_PERCENT)
            penalty_amount = max(1, penalty_amount)
            max_penalty = max(1, int(robber_balance * 0.5))
            penalty_amount = min(penalty_amount, max_penalty)
            
            await update_balance(robber_id, -penalty_amount)
            await update_balance(victim_id, penalty_amount)
            return "failed", 0, rob_percentage, penalty_amount, attempted_rob_amount
            
    except Exception as e:
        print(f"Error en attempt_robbery: {e}")
        return "error", 0, 0, 0, 0

def setup_command(economy_group, cog):
    """Configura el comando robar en el grupo economy"""
    
    @economy_group.command(name="robar", description="Intenta robar monedas a otro usuario (riesgo moderado)")
    @app_commands.describe(usuario="El usuario al que quieres robar")
    async def robar(interaction: discord.Interaction, usuario: discord.User):
        robber_id = str(interaction.user.id)
        robber_username = interaction.user.name
        victim_id = str(usuario.id)
        victim_username = usuario.name
        
        if robber_id == victim_id:
            embed = discord.Embed(
                title="❌ Robo Fallido",
                description="No puedes robarte a ti mismo!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Verificar cooldown
        last_rob = await get_rob_cooldown(robber_id)
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
        result, amount, percentage, penalty, attempted_amount = await attempt_robbery(
            robber_id, victim_id, robber_username, victim_username
        )
        
        # Actualizar cooldown si el robo se intentó realmente
        if result not in ["insufficient_funds", "victim_poor", "error"]:
            await update_rob_cooldown(robber_id)
        
        # Obtener nuevo balance del ladrón
        robber_new_data = await get_player(robber_id, robber_username)
        robber_new_balance = robber_new_data["balance"] if robber_new_data else 0
        
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
        
        elif result == "error":
            embed = discord.Embed(
                title="❌ Error",
                description="Ha ocurrido un error al procesar el robo.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        elif result == "success":
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

    @economy_group.command(name="estadisticas_robo", description="Muestra las estadísticas y expectativas del sistema de robos")
    async def estadisticas_robo(interaction: discord.Interaction):
        embed = discord.Embed(
            title="📈 Estadísticas del Sistema de Robos",
            description="¿Vale la pena robar? ¡Vamos a hacer cálculos!",
            color=discord.Color.blue()
        )
        
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
