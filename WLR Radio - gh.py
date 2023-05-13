
import discord
from discord.ext import commands
import asyncio
import ffmpeg
import json
from collections import deque
from discord import FFmpegPCMAudio

TOKEN = 'ENTER TOKEN HERE'

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix="!", intents=intents)

AUDIO_PATH = r'ENTER_PATH_TO_AUDIO_TRACKS'
AUDIO_FILES = [AUDIO_PATH+'\kevin-intro.m4a',
               AUDIO_PATH+'\Dreaming (Gibson Parker Remix) - Rootkit, Cammie Robinson -.mp3',
               AUDIO_PATH+'\imogen pre-voice.mp3',
               AUDIO_PATH+'\Imogen_Heap_-_Hide_and_Seek_Avicii_Remix.mp3',
               AUDIO_PATH+'\hardwell pre-voice.mp3',
               AUDIO_PATH+'\Hardwell - DOPAMINE (Extended Mix).mp3',
               AUDIO_PATH+'\Hardwell - REBELS NEVER DIE (Extended Mix)'
               ] #add as many as you need
FFMPEG_OPTIONS = {
    "options": "-vn -loglevel panic",
}
voice_clients = {}
connection_locks = {}
connection_tasks = {}
connecting = set()
last_connected_channels_file = "last_connected_channels.json"

def load_last_connected_channels():
    try:
        with open(last_connected_channels_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_last_connected_channel(guild_id, channel_id):
    data = load_last_connected_channels()
    data[str(guild_id)] = channel_id
    with open(last_connected_channels_file, "w") as f:
        json.dump(data, f)

last_connected_channels = load_last_connected_channels()

async def connect_and_play(voice_channel):
    print(f"Bot permissions in {voice_channel.name}: {voice_channel.permissions_for(voice_channel.guild.me)}")
    global CURRENT_AUDIO_SOURCE
    print(f"Attempting to connect to voice channel: {voice_channel.name} ({voice_channel.id})")
    try:
        if voice_channel.guild.voice_client is not None:
            print(f"Disconnecting from existing voice channel: {voice_channel.guild.voice_client.channel.name} ({voice_channel.guild.voice_client.channel.id})")
            await voice_channel.guild.voice_client.disconnect()
        voice_client = await asyncio.wait_for(voice_channel.connect(), timeout=10)
    except asyncio.TimeoutError:
        print(f"Connection to voice channel: {voice_channel.name} ({voice_channel.id}) timed out")
        return
    except Exception as e:
        print(f"Failed to connect to voice channel: {voice_channel.name} ({voice_channel.id}). Error: {e}")
        return

    save_last_connected_channel(voice_channel.guild.id, voice_channel.id)
    print(f"Connected to voice channel: {voice_channel.name} ({voice_channel.id})")
    queue = deque(AUDIO_FILES)
    while True:
        try:
            while voice_client.is_connected():
                if not queue:
                    queue.extend(AUDIO_FILES)
                audio_file = queue.popleft()
                print(f"Playing {audio_file} in {voice_channel.name} ({voice_channel.id})")
                CURRENT_AUDIO_SOURCE = FFmpegPCMAudio(audio_file, **FFMPEG_OPTIONS)
                voice_client.play(CURRENT_AUDIO_SOURCE)
                while voice_client.is_playing():
                    await asyncio.sleep(1)
            print(f"Voice client is not connected anymore. Breaking the loop.")
            break
        except Exception as e:
            print(f"Error occurred while playing audio: {e}")
            await asyncio.sleep(5)
    voice_client.stop()
    await voice_client.disconnect()
    print(f"Disconnected from voice channel: {voice_channel.name} ({voice_channel.id})")
@bot.event
async def on_voice_state_update(member, before, after):
    print(f"Voice state update: Member: {member}, Before: {before}, After: {after}")

    if member.bot:
        return

    if after.channel is None:
        return

    if before.channel == after.channel:
        return

    guild_id = after.channel.guild.id
    last_connected_channel = last_connected_channels.get(str(guild_id))
    if last_connected_channel is None or last_connected_channel == after.channel.id:
        if after.channel.guild.voice_client is not None:
            return
        global connection_tasks
        if guild_id not in connection_tasks:
            task = asyncio.create_task(connect_and_play(after.channel))
            connection_tasks[guild_id] = task
    else:
        channel = bot.get_channel(last_connected_channel)
        if channel is not None and channel.guild.voice_client is None:
            print(f"Reconnecting to last connected voice channel: {channel.name} ({channel.id})")
            task = asyncio.create_task(connect_and_play(channel))
            connection_tasks[guild_id] = task

@bot.event
async def on_ready():
    for guild_id, channel_id in last_connected_channels.items():
        guild = bot.get_guild(int(guild_id))
        if guild is not None:
            channel = bot.get_channel(int(channel_id))
            if channel is not None and channel.guild.voice_client is None:
                task = asyncio.create_task(connect_and_play(channel))
                connection_tasks[int(guild_id)] = task
                await asyncio.sleep(2)
                

bot.run(TOKEN)