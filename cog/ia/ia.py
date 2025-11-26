import discord
from discord import app_commands
from discord.ext import commands
import requests
import json
import os
from typing import Optional
import re

class AICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = "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"
        self.model = "tngtech/deepseek-r1t-chimera:free"

    @app_commands.command(name="ia", description="Consulta a la IA del Bot")
    @app_commands.describe(
        mensaje="Tu mensaje para la IA",
        modelo="Modelo de IA a usar (opcional)"
    )
    async def ia_command(
        self, 
        interaction: discord.Interaction, 
        mensaje: str,
        modelo: Optional[str] = None
    ):
        """Comando para consultar a la IA mediante OpenRouter"""
        
        # Verificar si la API key está configurada
        if not self.api_key:
            embed = discord.Embed(
                title="❌ Error de Configuración",
                description="La API key de OpenRouter no está configurada.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Usar modelo personalizado si se proporciona
        current_model = modelo if modelo else self.model

        # Enviar mensaje de "pensando"
        await interaction.response.defer(thinking=True)

        try:
            # Realizar la solicitud a OpenRouter con instrucción de etiquetas
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/F-Society-Bot",
                    "X-Title": "F_Society Bot",
                },
                data=json.dumps({
                    "model": current_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "IMPORTANTE: Tu respuesta debe estar contenida EXCLUSIVAMENTE entre las etiquetas [RESPONSE] y [/RESPONSE]. "
                                "No incluyas ningún texto fuera de estas etiquetas. "
                                "No expliques tu proceso de pensamiento. "
                                "No agregues comentarios antes o después de las etiquetas. "
                                "Solo proporciona la respuesta directa y útil dentro de las etiquetas."
                            )
                        },
                        {
                            "role": "user", 
                            "content": mensaje
                        }
                    ],
                    "max_tokens": 1000
                }),
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                
                if "choices" in data and len(data["choices"]) > 0:
                    ai_response = data["choices"][0]["message"]["content"]
                    
                    # Extraer solo el contenido de la ÚLTIMA etiqueta [RESPONSE]
                    final_response = self._extract_last_response(ai_response)
                    
                    embed = discord.Embed(
                        title="🤖 Respuesta de la IA",
                        description=self._truncate_text(final_response, 4000),
                        color=discord.Color.purple(),
                        timestamp=discord.utils.utcnow()
                    )
                    
                    embed.add_field(
                        name="🧠 Modelo", 
                        value=current_model, 
                        inline=True
                    )
                    
                    if "usage" in data:
                        usage = data["usage"]
                        tokens_info = f"Prompt: {usage.get('prompt_tokens', 'N/A')} | Completion: {usage.get('completion_tokens', 'N/A')} | Total: {usage.get('total_tokens', 'N/A')}"
                        embed.add_field(
                            name="📊 Tokens", 
                            value=tokens_info, 
                            inline=True
                        )
                    
                    embed.set_footer(text=f"Solicitado por: {interaction.user.display_name}")
                    
                    await interaction.followup.send(embed=embed)
                    
                else:
                    embed = discord.Embed(
                        title="❌ Error en la respuesta",
                        description="La IA no devolvió una respuesta válida.",
                        color=discord.Color.orange()
                    )
                    await interaction.followup.send(embed=embed)
                    
            else:
                error_msg = f"Error {response.status_code}: {response.text}"
                embed = discord.Embed(
                    title="❌ Error de API",
                    description=self._truncate_text(error_msg, 2000),
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed)

        except requests.exceptions.Timeout:
            embed = discord.Embed(
                title="⏰ Timeout",
                description="La solicitud a la IA tardó demasiado tiempo.",
                color=discord.Color.orange()
            )
            await interaction.followup.send(embed=embed)
            
        except requests.exceptions.RequestException as e:
            embed = discord.Embed(
                title="❌ Error de Conexión",
                description=f"No se pudo conectar con el servicio de IA: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Error Inesperado",
                description=f"Ocurrió un error inesperado: {str(e)}",
                color=discord.Color.red()
            )
            await interaction.followup.send(embed=embed)

    def _extract_last_response(self, text: str) -> str:
        """
        Extrae el contenido de la ÚLTIMA etiqueta [RESPONSE] hasta la PRIMERA etiqueta [/RESPONSE] después de ella.
        
        Ejemplo:
        Input: "[RESPONSE] Hola 1 [RESPONSE] Muy buenas [/RESPONSE]"
        Output: "Muy buenas"
        """
        # Encontrar la última posición de [RESPONSE]
        last_response_pos = text.rfind('[RESPONSE]')
        
        if last_response_pos == -1:
            # No se encontró ninguna etiqueta [RESPONSE]
            return self._fallback_clean_response(text)
        
        # Encontrar la posición de [/RESPONSE] después de la última [RESPONSE]
        end_response_pos = text.find('[/RESPONSE]', last_response_pos)
        
        if end_response_pos == -1:
            # No se encontró la etiqueta de cierre después de la última [RESPONSE]
            # Intentar extraer todo desde la última [RESPONSE] hasta el final
            content = text[last_response_pos + len('[RESPONSE]'):].strip()
            return self._clean_additional_tags(content)
        
        # Extraer el contenido entre la última [RESPONSE] y la siguiente [/RESPONSE]
        content = text[last_response_pos + len('[RESPONSE]'):end_response_pos].strip()
        return self._clean_additional_tags(content)

    def _clean_additional_tags(self, text: str) -> str:
        """Limpia cualquier etiqueta adicional que pueda haber dentro del contenido"""
        # Remover cualquier [RESPONSE] o [/RESPONSE] que quede dentro
        text = text.replace('[RESPONSE]', '').replace('[/RESPONSE]', '')
        return text.strip()

    def _fallback_clean_response(self, text: str) -> str:
        """Método de respaldo para limpiar la respuesta si no encuentra etiquetas"""
        # Si no hay etiquetas, buscar el último bloque que parezca una respuesta
        lines = text.split('\n')
        cleaned_lines = []
        
        # Buscar desde el final hacia el principio
        in_response = False
        for line in reversed(lines):
            line = line.strip()
            if not line:
                continue
                
            # Si encontramos una línea que parece respuesta final, activamos el modo
            if any(phrase in line.lower() for phrase in ['¡', '¿', 'hello', 'hi ', 'hola', 'buenas']):
                in_response = True
                
            if in_response and not any(phrase in line.lower() for phrase in [
                'first,', 'then,', 'finally,', 'i should', 'i need to', 
                'the user', 'let me', 'okay,', 'so,', 'well,', 'therefore,',
                'primero', 'luego', 'finalmente', 'debo', 'necesito',
                'el usuario', 'déjame', 'vale,', 'bueno,', 'por lo tanto,',
                'step 1', 'step 2', 'step 3', 'paso 1', 'paso 2', 'paso 3'
            ]):
                cleaned_lines.insert(0, line)  # Insertar al principio para mantener orden
        
        result = '\n'.join(cleaned_lines)
        
        # Si no queda nada útil, devolver el texto original con una nota
        if not result.strip():
            return f"[El modelo no usó las etiquetas correctamente]\n\n{text}"
            
        return result

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Trunca el texto si excede el límite de caracteres"""
        if len(text) > max_length:
            return text[:max_length-3] + "..."
        return text

async def setup(bot):
    await bot.add_cog(AICog(bot))
