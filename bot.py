import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

# =====================
# CONFIGURAÇÕES
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

FFMPEG_PATH = "ffmpeg"

queues = {}

# =====================
# EVENTOS
# =====================
@bot.event
async def on_ready():
    print(f"Bot conectado como {bot.user}")

# =====================
# COMANDOS
# =====================
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        canal = ctx.author.voice.channel
        await canal.connect()
        await ctx.send(f"Conectado em {canal}")
    else:
        await ctx.send("Você precisa estar em um canal de voz")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        queues.pop(ctx.guild.id, None)
        await ctx.send("Desconectado")
    else:
        await ctx.send("Não estou em um canal")

@bot.command()
async def play(ctx, url):

    guild_id = ctx.guild.id

    if not ctx.author.voice:
        return await ctx.send("Entre em um canal de voz primeiro")

    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    if guild_id not in queues:
        queues[guild_id] = []

    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'extract_flat': False,
        'skip_download': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if 'entries' in info:

            count = 0

            for entry in info['entries']:
                if entry:
                    queues[guild_id].append(
                        f"https://www.youtube.com/watch?v={entry['id']}"
                    )
                    count += 1

            await ctx.send(f"Playlist adicionada: {count} músicas")

        else:
            queues[guild_id].append(url)
            await ctx.send("Música adicionada à fila")

        if not ctx.voice_client.is_playing():
            await play_next(ctx)

    except Exception as e:
        await ctx.send(f"Erro ao adicionar música: {e}")

async def play_next(ctx):

    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if guild_id not in queues or len(queues[guild_id]) == 0:
        return await ctx.send("Fila vazia")

    url = queues[guild_id][0]

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        }
    }

    ffmpeg_opts = {
        'executable': FFMPEG_PATH,
        'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
        'options': '-vn'
    }

    try:

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            audio_url = info['url']

        source = discord.FFmpegPCMAudio(audio_url, **ffmpeg_opts)

        vc.play(
            source,
            after=lambda e: asyncio.run_coroutine_threadsafe(
                after_play(ctx), bot.loop
            )
        )

        await ctx.send(f"Tocando agora: {info.get('title','Música')}")

    except Exception as e:

        await ctx.send(f"Erro ao tocar música: {e}")
        queues[guild_id].pop(0)

        if queues[guild_id]:
            await play_next(ctx)

async def after_play(ctx):

    guild_id = ctx.guild.id
    queues[guild_id].pop(0)

    if queues[guild_id]:
        await play_next(ctx)

@bot.command()
async def skip(ctx):

    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Música pulada")

    else:
        await ctx.send("Não há música tocando")

@bot.command()
async def stop(ctx):

    if ctx.voice_client and ctx.voice_client.is_playing():

        ctx.voice_client.stop()
        guild_id = ctx.guild.id
        queues[guild_id] = []

        await ctx.send("Fila limpa e música parada")

    else:
        await ctx.send("Não há música tocando")

@bot.command()
async def queue(ctx):

    guild_id = ctx.guild.id

    if guild_id in queues and queues[guild_id]:

        msg = "\n".join(
            [f"{i+1}. {q}" for i, q in enumerate(queues[guild_id])]
        )

        await ctx.send(f"Fila atual:\n{msg}")

    else:
        await ctx.send("Fila vazia")

@bot.command(name="help")
async def help_command(ctx):

    embed = discord.Embed(
        title="Comandos do Bot de Música",
        color=discord.Color.blue()
    )

    embed.add_field(name="!join", value="entra no canal", inline=False)
    embed.add_field(name="!leave", value="sai do canal", inline=False)
    embed.add_field(name="!play <url>", value="toca música ou playlist", inline=False)
    embed.add_field(name="!skip", value="pula música", inline=False)
    embed.add_field(name="!stop", value="para música", inline=False)
    embed.add_field(name="!queue", value="mostra fila", inline=False)

    await ctx.send(embed=embed)

# =====================
# RODAR BOT
# =====================
bot.run(TOKEN)
