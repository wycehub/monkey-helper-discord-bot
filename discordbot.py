import json
import random
import discord
import yt_dlp
import os
import asyncio
import re
import datetime
import urllib.parse
import aiohttp
import asyncpraw
import sys
import dislash
from aiohttp import ClientSession
from discord import FFmpegPCMAudio
from discord.ext import commands

#intitialize bot
def placeholder_prefix(*args, **kwargs):
    return "!"

bot = commands.Bot(command_prefix=placeholder_prefix(), intents=discord.Intents.all())
bot.remove_command('help')

def initialize_files():
    if not os.path.exists("secrets.json"):
        secrets = {
            "discord_bot_key": "YOUR_DISCORD_BOT_TOKEN",
            "omdb_api_key": "YOUR_OMDB_API_KEY",
            "guild_id": "YOUR_GUILD_ID",
            "reddit_client_id": "YOUR_REDDIT_CLIENT_ID",
            "reddit_secret": "YOUR_REDDIT_SECRET",
            "reddit_user_agent": "YOUR_REDDIT_USER_AGENT"
        }
        with open("secrets.json", "w") as file:
            json.dump(secrets, file)
            print("a new secrets.json file has been created for you,provide your API keys and tokens in the file and then run the script again")
        sys.exit()
    if not os.path.exists("prefixes.json"):
        default_prefixes = {str(guild.id): "!" for guild in bot.guilds}
        with open("prefixes.json", "w") as file:
            json.dump(default_prefixes, file)
    for guild in bot.guilds:
        filename = f"{guild.id}_movies.json"
        if not os.path.exists(filename):
            with open(filename, "w") as file:
                json.dump({"watch": [], "watched": []}, file)

initialize_files()

def get_prefix(bot, message):
    with open("prefixes.json", "r") as file:
        prefixes = json.load(file)
    return prefixes.get(str(message.guild.id), "!")

with open("secrets.json", "r") as file:
    secrets = json.load(file)
    TOKEN = secrets["discord_bot_key"]
    API_KEY = secrets["omdb_api_key"]
    GUILD_ID = secrets["guild_id"]
    REDDIT_CLIENT_ID = secrets["reddit_client_id"]
    REDDIT_SECRET = secrets["reddit_secret"]
    REDDIT_USER_AGENT = secrets["reddit_user_agent"]

async def set_bot_activity():
    guilds_prefixes = {}
    with open("prefixes.json", "r") as file:
        prefixes = json.load(file)

    for guild in bot.guilds:
        guild_prefix = prefixes.get(str(guild.id), "!")
        guilds_prefixes[str(guild.id)] = guild_prefix

    for guild, prefix in guilds_prefixes.items():
        activity = discord.Game(name=f"listening for {prefix}help")
        await bot.change_presence(activity=activity)

@bot.event
async def on_ready():
    bot.session = aiohttp.ClientSession()
    reddit = asyncpraw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        requestor_kwargs={"session": bot.session},
    )
    bot.reddit = reddit
    print(f'{bot.user.name} connected to these guilds:')
    for guild in bot.guilds:
        print(f' - {guild.name} (id: {guild.id})')
        initialize_files()
    
    await set_bot_activity()

@bot.event
async def on_disconnect():
    await bot.session.close()

@bot.event
async def on_guild_join(guild):
    with open("prefixes.json", "r") as file:
        prefixes = json.load(file)
    prefixes[str(guild.id)] = "!"
    with open("prefixes.json", "w") as file:
        json.dump(prefixes, file)

@bot.event
async def on_guild_remove(guild):
    with open("prefixes.json", "r") as file:
        prefixes = json.load(file)
    prefixes.pop(str(guild.id))
    with open("prefixes.json", "w") as file:
        json.dump(prefixes, file)

# help
@bot.command()
async def help(ctx, command: str = None):
    prefix = get_prefix(bot, ctx.message)
    if not command:
        embed = discord.Embed(title="help", description="list of available commands", color=0x00BFFF)
        embed.add_field(name="audio commands", value=f"`{prefix}a play [url]` - play audio from a youtube url\n"
                                                     f"`{prefix}a stop` - stop playing audio\n"
                                                     f"`{prefix}a skip` - skip the current audio\n"
                                                     f"`{prefix}a queue` - show the audio queue\n"
                                                     f"`{prefix}a remove [index]` - remove a song from the queue",
                        inline=False)
        embed.add_field(name="movie commands", value=f"`{prefix}m add` - look for the title and add it\n"
                                                     f"`{prefix}m watched [title]` - add a movie to the watched list\n"
                                                     f"`{prefix}m remove [title]` - remove a title from the lists\n"
                                                     f"`{prefix}m list [title]` - display watch and watched list\n"
                                                     f"`{prefix}m random` - select a random movie from the watch list",
                        inline=False)
        embed.add_field(name="other commands", value=f"`{prefix}monkey` - post a random monkey image\n"
                                                     f"`{prefix}rng [max_number]` - random number between 1 and max_number\n"
                                                     f"`{prefix}prefix [new_prefix]` - change the bot's command prefix",
                        inline=False)
    else:
        command = command.lower()
        if command == "a" or command == "audio":
            help_text = f"**{prefix}a play [url]** - play audio from a YouTube URL\n"\
                        f"**{prefix}a stop** - stop playing audio\n"\
                        f"**{prefix}a skip** - skip the current audio\n"\
                        f"**{prefix}a queue** - show the audio queue\n"\
                        f"**{prefix}a remove [index]** - remove a song from the queue"
        elif command == "m" or command == "movie":
            help_text = f"**{prefix}m add [title]** - look for the title and add it\n"\
                        f"**{prefix}m watched [title]** - add a movie to the watched list\n"\
                        f"**{prefix}m remove [title]** - remove a title from the lists\n"\
                        f"**{prefix}m list [title]** - display watch and watched list\n"\
                        f"**{prefix}m random** - select a random movie from the watch list"
        elif command == "monkey":
            help_text = f"**{prefix}monkey** - post a random monkey image"
        elif command == "rng":
            help_text = f"**{prefix}rng [max_number]** - random number between 1 and max_number\n"
        elif command == "prefix":
            help_text = f"**{prefix}prefix [new_prefix]** - change the bot's command prefix"
        else:
            help_text = "invalid command name. type `!help` for the list of available commands"
            embed = discord.Embed(title=f"Help: {command}", description=help_text, color=0x00BFFF)
    await ctx.send(embed=embed)

# monkey
async def fetch_reddit_monkey():
    async with aiohttp.ClientSession() as session:
        auth = aiohttp.BasicAuth(REDDIT_CLIENT_ID, REDDIT_SECRET)
        data = {
            'grant_type': 'client_credentials',
            'scope': 'read'
        }
        async with session.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data) as token_response:
            token_data = await token_response.json()
            access_token = token_data['access_token']
            headers = {
                'Authorization': f"Bearer {access_token}",
                'User-Agent': 'DiscordBot/1.0'
            }
            async with session.get('https://oauth.reddit.com/r/monke/hot', headers=headers, params={'limit': 100}) as response:
                data = await response.json()
                posts = data['data']['children']
                image_posts = [post for post in posts if post['data']['post_hint'] in ('image', 'rich:video')]
                return random.choice(image_posts)['data']['url']

@bot.command()
async def monkey(ctx):
    subreddit = await bot.reddit.subreddit("monke")
    post = None
    post_type = "unknown"

    while post_type not in {"image", "gif"}:
        posts = [post async for post in subreddit.hot(limit=50)]
        post = random.choice(posts)
        post_hint = getattr(post, "post_hint", None)
        if post_hint:
            if post_hint == "image":
                post_type = "image"
            elif post_hint == "rich:video" and "gif" in post.url:
                post_type = "gif"
        else:
            post_type = "unknown"

    if post_type in {"image", "gif"}:
        await ctx.send(post.url)
    else:
        await ctx.send("unable to fetch monkey image/gif")

# rng
@bot.command()
async def rng(ctx, max_number: int = 100):
    random_number = random.randint(1, max_number)
    await ctx.send(f"random number between 1 and {max_number}: {random_number}")

# prefix
async def update_bot_activity(ctx, new_prefix):
    activity = discord.Game(name=f"listening for {new_prefix}help")
    await bot.change_presence(activity=activity)

@bot.command()
@commands.has_permissions(administrator=True)
async def prefix(ctx, new_prefix):
    with open("prefixes.json", "r") as file:
        prefixes = json.load(file)
    prefixes[str(ctx.guild.id)] = new_prefix
    with open("prefixes.json", "w") as file:
        json.dump(prefixes, file)
    await ctx.send(f"prefix changed to: {new_prefix}")
    await update_bot_activity(ctx, new_prefix)

@prefix.error
async def prefix_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("you don't have the required permissions to change the prefix")

# youtube audio
YDL_OPTIONS = {
    'format': 'bestaudio/best',
    'quiet': True,
    'noplaylist': False,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
}

queue = []
current_song = None
is_playing = False
inactive_vc_timers = {}

async def check_inactivity_and_leave(ctx):
    guild_id = ctx.guild.id
    while True:
        await asyncio.sleep(300)
        if ctx.voice_client and ctx.voice_client.is_playing():
            continue
        if ctx.guild.voice_client is not None:
            await ctx.guild.voice_client.disconnect()
            inactive_vc_timers[guild_id].cancel()
            del inactive_vc_timers[guild_id]
            break

async def connect_to_voice_channel(ctx):
    voice_channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    if voice_client is not None:
        await voice_client.move_to(voice_channel)
    else:
        voice_client = await voice_channel.connect()
    guild_id = ctx.guild.id
    if guild_id in inactive_vc_timers:
        inactive_vc_timers[guild_id].cancel()
    else:
        inactive_vc_timers[guild_id] = asyncio.create_task(check_inactivity_and_leave(ctx))
    return voice_client

async def get_video_info(search, is_playlist=False):
    ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)
    if is_playlist:
        info = ytdl.extract_info(search, download=False)
        if "entries" not in info:
            return []
        playlist_items = [
            {
                "url": f'https://www.youtube.com/watch?v={entry["id"]}',
                "title": entry["title"],
                "duration": entry["duration"],
            }
            for entry in info["entries"]
        ]
        return playlist_items
    else:
        if "youtube.com" in search or "youtu.be" in search:
            video_url = search
        else:
            search_url = f'https://www.youtube.com/results?search_query={search}'
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url) as response:
                    webpage = await response.text()
                    video_id = re.search(
                        r"watch\?v=(\S{11})", webpage
                    ).group()
                    video_url = f'https://www.youtube.com/{video_id}'
        info = ytdl.extract_info(video_url, download=False)
        return {
            "url": video_url,
            "title": info["title"],
            "duration": info["duration"],
        }

async def play_audio(ctx):
    if not queue:
        global is_playing
        is_playing = False
        return
    url, title, duration = queue.pop(0)
    global current_song
    current_song = {"url": url, "title": title, "duration": duration}
    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -nostdin",
        "options": "-vn -acodec pcm_s16le -ac 2 -ar 48000 -loglevel error",
    }
    ytdl_options = {
        'format': 'bestaudio/best',
        'quiet': True,
    }
    ytdl = yt_dlp.YoutubeDL(YDL_OPTIONS)
    info = ytdl.extract_info(url, download=False)
    url2 = info['url']
    voice_client = await connect_to_voice_channel(ctx)
    player = discord.FFmpegPCMAudio(url2, **FFMPEG_OPTIONS)
    voice_client.play(player, after=lambda e: asyncio.run_coroutine_threadsafe(play_audio(ctx), bot.loop))
    await ctx.send(f"now playing: {title}")

async def process_queue(ctx):
    global is_playing
    if not is_playing:
        is_playing = True
        voice_client = await connect_to_voice_channel(ctx)
        await play_audio(ctx)

@bot.group(name="a")
async def audio(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("use a valid subcommand: play, stop, skip, queue, remove")

@audio.command(name="play")
async def a_play(ctx, *, search: str):
    playlist_pattern = r"(?:https?:\/\/)?(?:www\.)?youtube\.com\/playlist\?(?=.*list=)"
    if re.match(playlist_pattern, search):
        info = await get_video_info(search, is_playlist=True)
        for song in info:
            queue.append((song['url'], song['title'], song['duration']))
        await ctx.send(f"added playlist to the queue")
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            await play_audio(ctx)
        return
    info = await get_video_info(search)
    title = info['title']
    final_url = info['url']
    video_length = info['duration']
    queue.append((final_url, title, video_length))
    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await play_audio(ctx)
    else:
        await ctx.send(f"added to queue: {title}")

@audio.command(name="stop")
async def a_stop(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()
        queue.clear()

@audio.command(name="skip")
async def a_skip(ctx):
    if ctx.voice_client:
        ctx.voice_client.stop()

@audio.command(name="queue")
async def a_queue(ctx):
    if not queue and not is_playing:
        await ctx.send("there are no songs in the queue")
        return
    else:
        await ctx.send(f"currently playing: {current_song['title']} [{str(datetime.timedelta(seconds=current_song['duration']))}]",)
        embed = discord.Embed(title="queue", color=discord.Color.green())
        for idx, song in enumerate(queue, start=1):
            title = song[1]
            duration = song[2]
            embed.add_field(
                name=f"{idx}. {title} [{str(datetime.timedelta(seconds=duration))}]",
                value="\u200b",
                inline=False,
            )
        await ctx.send(embed=embed)

@audio.command(name="remove")
async def a_remove(ctx, index: int):
    try:
        removed_item = queue.pop(index - 1)
        await ctx.send(f"removed {removed_item[1]}")
    except IndexError:
        await ctx.send("invalid index")

# movie library
def add_movie_to_list(ctx, movie_title: str, list_name: str):
    with open(f"{ctx.guild.id}_movies.json", "r") as file:
        movie_list = json.load(file)
    movie_list[list_name].append(movie_title)
    with open(f"{ctx.guild.id}_movies.json", "w") as file:
        json.dump(movie_list, file)

def remove_movie_from_list(ctx, movie_title: str, list_name: str):
    with open(f"{ctx.guild.id}_movies.json", "r") as file:
        movie_list = json.load(file)
    movie_title = movie_title.lower()
    for title in movie_list[list_name]:
        if title.lower() == movie_title:
            movie_list[list_name].remove(title)
            break
    with open(f"{ctx.guild.id}_movies.json", "w") as file:
        json.dump(movie_list, file)


def move_movie_to_watched_list(ctx, movie_title: str):
    remove_movie_from_list(ctx, movie_title, "watch")
    add_movie_to_list(ctx, movie_title, "watched")

def move_movie_to_watch_list(ctx, movie_title: str):
    remove_movie_from_list(ctx, movie_title, "watched")
    add_movie_to_list(ctx, movie_title, "watch")

def generate_movie_embed(movie_data: dict):
    embed = discord.Embed(title=movie_data["Title"], color=0x00BFFF)
    embed.set_thumbnail(url=movie_data["Poster"])
    embed.add_field(name="Year", value=movie_data["Year"], inline=True)
    embed.add_field(name="Rated", value=movie_data["Rated"], inline=True)
    embed.add_field(name="Runtime", value=movie_data["Runtime"], inline=True)
    embed.add_field(name="Genre", value=movie_data["Genre"], inline=True)
    embed.add_field(name="Director", value=movie_data["Director"], inline=True)
    embed.add_field(name="Actors", value=movie_data["Actors"], inline=True)
    embed.add_field(name="Plot", value=movie_data["Plot"], inline=False)
    return embed

def get_random_movie(ctx):
    with open(f"{ctx.guild.id}_movies.json", "r") as file:
        movie_list = json.load(file)
    watch_list = movie_list["watch"]
    if watch_list:
        return random.choice(watch_list)
    else:
        return None

async def get_movie_data(title: str):
    encoded_title = urllib.parse.quote(title)
    search_url = f'http://www.omdbapi.com/?apikey={API_KEY}&s={encoded_title}'
    async with ClientSession() as session:
        async with session.get(search_url) as response:
            search_results = await response.json()
            if search_results.get("Response") == "True":
                best_match = search_results["Search"][0]
                title = best_match["Title"]
                movie_url = f'http://www.omdbapi.com/?apikey={API_KEY}&t={title}'
                async with session.get(movie_url) as movie_response:
                    movie_data = await movie_response.json()
                    if movie_data.get("Response") == "True":
                        return movie_data
                    else:
                        return None
            else:
                return None

async def wait_for_reaction(bot, message, author, valid_reactions):
    def check(reaction, user):
        return user == author and str(reaction.emoji) in valid_reactions and reaction.message.id == message.id and not user.bot
    try:
        reaction, user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
    except asyncio.TimeoutError:
        return None
    else:
        return str(reaction.emoji)

@bot.group(name="m")
async def movie(ctx):
    if ctx.invoked_subcommand is None:
        await ctx.send("please use a valid subcommand: add, remove, watched, list")

@movie.command(name="add")
async def m_add(ctx, *, title: str):
    movie_data = await get_movie_data(title)
    if movie_data:
        with open(f"{ctx.guild.id}_movies.json", "r") as file:
            movie_list = json.load(file)
        movie_title = movie_data["Title"]
        movie_title_lower = movie_title.lower()
        already_in_watch = any(title.lower() == movie_title_lower for title in movie_list["watch"])
        already_in_watched = any(title.lower() == movie_title_lower for title in movie_list["watched"])
        if already_in_watch:
            await ctx.send(f"{movie_title} is already in the watch list")
            return
        if already_in_watched:
            embed = generate_movie_embed(movie_data)
            message = await ctx.send(embed=embed)
            message = await ctx.send("this movie is already in the watched list. do you want to add it back to the watch list?")
            for emoji in ("✅", "❌"):
                await message.add_reaction(emoji)
            reaction = await wait_for_reaction(bot, message, ctx.author, ["✅", "❌"])
            await message.clear_reactions()
            if reaction == "✅":
                move_movie_to_watch_list(ctx, movie_data["Title"])
                await ctx.send(f"moved {movie_data['Title']} back to the watch list")
            elif reaction == "❌":
                await ctx.send("cancelled")
            return
        embed = generate_movie_embed(movie_data)
        message = await ctx.send(embed=embed)
        message = await ctx.send("is this the movie you want to add?")
        for emoji in ("✅", "❌"):
            await message.add_reaction(emoji)
        reaction = await wait_for_reaction(bot, message, ctx.author, ["✅", "❌"])
        await message.clear_reactions()
        if reaction == "✅":
            add_movie_to_list(ctx, movie_data["Title"], "watch")
            await ctx.send(f"added {movie_data['Title']} to the watch list")
        elif reaction == "❌":
            await ctx.send("cancelled")
    else:
        await ctx.send("movie not found")
  
@movie.command(name="remove")
async def m_remove(ctx, *, title: str):
    remove_movie_from_list(ctx, title, "watch")
    remove_movie_from_list(ctx, title, "watched")
    await ctx.send(f"removed {title}")

@movie.command(name="watched")
async def m_watched(ctx, *, title: str):
    movie_data = await get_movie_data(title)
    if movie_data:
        move_movie_to_watched_list(ctx, movie_data["Title"])
        await ctx.send(f"added {movie_data['Title']} to the watched list")
    else:
        await ctx.send("movie not found")

@movie.command(name="list")
async def m_list(ctx):
    with open(f"{ctx.guild.id}_movies.json", "r") as file:
        movie_list = json.load(file)
    watch_list = movie_list["watch"]
    watched_list = movie_list["watched"]
    watch_list_str = "\n".join(watch_list) if watch_list else "no movies in the watch list"
    watched_list_str = "\n".join(watched_list) if watched_list else "no movies in the watched list"
    response = f"**watch list:**\n{watch_list_str}\n\n**watched List:**\n{watched_list_str}"
    await ctx.send(response)

@movie.command(name="random")
async def m_random(ctx):
    random_movie = get_random_movie(ctx)
    if random_movie:
        await ctx.send(f"Random movie from the watch list: {random_movie}")
    else:
        await ctx.send("The watch list is empty.")

bot.run(TOKEN)
