import discord
from discord import app_commands
from discord.ext import commands
import os
import importlib
import sys
import random
import asyncio
import sqlite3

# Grupo de comandos de blackjack
blackjack_group = app_commands.Group(
    name="blackjack", 
    description="Comandos para jugar al Blackjack",
    default_permissions=None
)

# Funciones de utilidad para blackjack
def calculate_hand_value(hand):
    value, aces = 0, 0
    for card in hand:
        rank = card[:-1]
        if rank in ["J", "Q", "K"]:
            value += 10
        elif rank == "A":
            value += 11
            aces += 1
        else:
            value += int(rank)
    while value > 21 and aces:
        value -= 10
        aces -= 1
    return value

def draw_card(deck):
    return deck.pop(random.randint(0, len(deck) - 1))

def create_deck():
    suits = ["♥", "♦", "♣", "♠"]
    ranks = [str(i) for i in range(2, 11)] + ["J", "Q", "K", "A"]
    return [r + s for r in ranks for s in suits]

def format_hand(hand):
    formatted_cards = []
    for card in hand:
        suit = card[-1]
        rank = card[:-1]
        suit_emoji = {
            "♥": "❤️", "♦": "♦️", "♣": "♣️", "♠": "♠️"
        }.get(suit, suit)
        formatted_cards.append(f"{rank}{suit_emoji}")
    return " | ".join(formatted_cards)

def format_card(card):
    suit = card[-1]
    rank = card[:-1]
    suit_emoji = {
        "♥": "❤️", "♦": "♦️", "♣": "♣️", "♠": "♠️"
    }.get(suit, suit)
    return f"{rank}{suit_emoji}"

# Clase de botones para blackjack
class BlackjackButtons(discord.ui.View):
    def __init__(self, player, hand, deck, bet_amount, timeout=30):
        super().__init__(timeout=timeout)
        self.player = player
        self.hand = hand
        self.deck = deck
        self.bet_amount = bet_amount
        self.value = calculate_hand_value(hand)
        self.ended = False

    async def on_timeout(self):
        if not self.ended:
            self.ended = True
            for item in self.children:
                item.disabled = True
            
            embed = discord.Embed(
                title="⏰ Tiempo Agotado",
                description=f"{self.player.mention} se quedó sin tiempo.",
                color=discord.Color.orange()
            )
            embed.add_field(name="Mano Final", value=f"```{format_hand(self.hand)}```", inline=False)
            embed.add_field(name="Valor", value=f"**{self.value} puntos**", inline=True)
            embed.add_field(name="Apuesta", value=f"**{self.bet_amount:,}** 💰", inline=True)
            
            await self.message.edit(embed=embed, view=self)
            self.stop()

    @discord.ui.button(label="PEDIR CARTA", style=discord.ButtonStyle.success, custom_id="hit", emoji="🃏")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
            return
        
        card = draw_card(self.deck)
        self.hand.append(card)
        self.value = calculate_hand_value(self.hand)
        
        embed = discord.Embed(
            title=f"🎴 Turno de {self.player.display_name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="Tu Mano", value=f"```{format_hand(self.hand)}```", inline=False)
        embed.add_field(name="Valor Actual", value=f"**{self.value} puntos**", inline=True)
        embed.add_field(name="Apuesta", value=f"**{self.bet_amount:,}** 💰", inline=True)
        
        if self.value > 21:
            self.ended = True
            for item in self.children:
                item.disabled = True
            embed.title = "💥 ¡Te Pasaste de 21!"
            embed.color = discord.Color.red()
            embed.description = f"{self.player.mention} se pasó de 21."
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
        else:
            embed.description = "¿Quieres otra carta o te plantas?"
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="PLANTARSE", style=discord.ButtonStyle.danger, custom_id="stand", emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.player:
            await interaction.response.send_message("❌ No es tu turno.", ephemeral=True)
            return
        
        self.ended = True
        for item in self.children:
            item.disabled = True
        
        embed = discord.Embed(
            title="✋ Te Has Plantado",
            description=f"{self.player.mention} decide plantarse.",
            color=discord.Color.green()
        )
        embed.add_field(name="Mano Final", value=f"```{format_hand(self.hand)}```", inline=False)
        embed.add_field(name="Valor Final", value=f"**{self.value} puntos**", inline=True)
        embed.add_field(name="Apuesta", value=f"**{self.bet_amount:,}** 💰", inline=True)
        
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

class BlackJackCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.loaded_commands = []
        self.current_bet_min = 0
        self.player_bets = {}

    async def load_blackjack_commands(self):
        """Carga automáticamente todos los comandos de la carpeta blackjack"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        blackjack_commands_path = os.path.join(current_dir, "blackjack")
        
        if not os.path.exists(blackjack_commands_path):
            print("❌ No se encuentra la carpeta blackjack")
            return

        if blackjack_commands_path not in sys.path:
            sys.path.append(blackjack_commands_path)

        for filename in os.listdir(blackjack_commands_path):
            if filename.endswith(".py") and filename not in ["__init__.py", "blackjack.py"]:
                module_name = filename[:-3]
                try:
                    # Importar usando importlib con ruta absoluta
                    spec = importlib.util.spec_from_file_location(
                        module_name, 
                        os.path.join(blackjack_commands_path, filename)
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    if hasattr(module, 'setup_command'):
                        module.setup_command(blackjack_group, self)
                        self.loaded_commands.append(module_name)
                        print(f"✅ Comando blackjack cargado: {module_name}")
                    else:
                        print(f"⚠️  Módulo {module_name} no tiene función setup_command")
                        
                except Exception as e:
                    print(f"❌ Error al cargar {filename}: {e}")

    async def cog_load(self):
        await self.load_blackjack_commands()

async def setup(bot):
    bot.tree.add_command(blackjack_group)
    blackjack_cog = BlackJackCog(bot)
    await bot.add_cog(blackjack_cog)
