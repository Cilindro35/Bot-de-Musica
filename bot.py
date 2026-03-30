import discord
from discord.ext import commands
import yt_dlp
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()  # carrega as variáveis do .env

TOKEN = os.getenv("DISCORD_TOKEN")


# =====================
# CONFIGURAÇÕES
# =====================
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Caminho completo do FFmpeg no Windows
FFMPEG_PATH = r"C:\Users\felli\Downloads\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe"

# Fila de músicas por guilda
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
        await ctx.send("Você precisa estar em um canal de voz!")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        queues.pop(ctx.guild.id, None)
        await ctx.send("Desconectado do canal!")
    else:
        await ctx.send("Não estou em um canal!")

@bot.command()
async def play(ctx, url):
    guild_id = ctx.guild.id

    if not ctx.author.voice:
        return await ctx.send("Entre em um canal de voz primeiro!")

    # Conecta se não estiver
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    if guild_id not in queues:
        queues[guild_id] = []

    # Configura yt_dlp para suportar playlists e JS runtime
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'extract_flat': True,  # pega apenas URLs da playlist
        'js_runtime': 'node'
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        # Se for playlist, adiciona todos os vídeos
        if 'entries' in info:
            for entry in info['entries']:
                queues[guild_id].append(entry['url'])
            await ctx.send(f"Playlist adicionada! {len(info['entries'])} músicas na fila.")
        
        else:
            queues[guild_id].append(info['url'])
            await ctx.send(f"Música adicionada à fila!")

        # Se não está tocando, começa
        if not ctx.voice_client.is_playing():
            await play_next(ctx)

    except Exception as e:
        await ctx.send(f"Erro ao adicionar música: {e}")

async def play_next(ctx):
    guild_id = ctx.guild.id
    vc = ctx.voice_client

    if guild_id not in queues or len(queues[guild_id]) == 0:
        return await ctx.send("Fila vazia!")

    url = queues[guild_id][0]

    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'js_runtime': 'node'
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
        vc.play(source, after=lambda e: asyncio.run_coroutine_threadsafe(after_play(ctx), bot.loop))
        await ctx.send(f"Tocando agora: {info.get('title', 'Música')}")
    
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
        await ctx.send("Música pulada!")
    
    else:
        await ctx.send("Não há música tocando!")

@bot.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        guild_id = ctx.guild.id
        queues[guild_id] = []
        await ctx.send("Música parada e fila limpa!")
   
    else:
        await ctx.send("Não há música tocando!")

@bot.command()
async def queue(ctx):
    guild_id = ctx.guild.id
    if guild_id in queues and queues[guild_id]:
        msg = "\n".join([f"{i+1}. {q}" for i, q in enumerate(queues[guild_id])])
        await ctx.send(f"Fila atual:\n{msg}")
    
    else:
        await ctx.send("Fila vazia!")

@bot.command(name='help')
async def help_command(ctx):
    embed = discord.Embed(title="Comandos do Bot de Música", color=discord.Color.blue())
    embed.add_field(name="!join", value="Faz o bot entrar no seu canal de voz.", inline=False)
    embed.add_field(name="!leave", value="Faz o bot sair do canal de voz.", inline=False)
    embed.add_field(name="!play <url>", value="Toca a música ou playlist do YouTube.", inline=False)
    embed.add_field(name="!skip", value="Pula a música atual.", inline=False)
    embed.add_field(name="!stop", value="Para a música e limpa a fila.", inline=False)
    embed.add_field(name="!queue", value="Mostra a fila atual de músicas.", inline=False)
    embed.add_field(name="!help", value="Mostra esta mensagem de ajuda.", inline=False)
    await ctx.send(embed=embed)

# =====================
# RODA O BOT
# =====================
bot.run(TOKEN)

