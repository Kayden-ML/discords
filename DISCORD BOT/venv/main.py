from typing import Final
import os
import aiohttp
import discord
import json
from dotenv import load_dotenv
from discord import Intents, Message, Interaction
from discord.ext import tasks, commands
from datetime import datetime, timezone
from discord import app_commands
from flask import ctx

load_dotenv()
TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')
session_store = {}

intents: Intents = Intents.default()
intents.message_content = True
bot: commands.Bot = commands.Bot(command_prefix="!", intents=intents)





@bot.event
async def on_ready() -> None:
    print(f'{bot.user} is now running!')
    fetch_and_send_schedule.start()
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

@bot.command()
async def api(ctx):
    async with aiohttp.ClientSession() as session:
        discord_id = ctx.author.id
        async with session.get("http://127.0.0.1:5000/api/recommendations?discord_id={discord_id}") as r:
            if r.status == 200:
                await ctx.send("Working!")
            else:
                await ctx.send(f"Can't get API" + str(r.status))

@bot.tree.command(name="recommendation")
async def recommendation(interaction: discord.Interaction):
    async with aiohttp.ClientSession() as session:
        async with session.get("http://127.0.0.1:5000/api/recommendations?discord_id={discord_id}") as r:
            recommendations = await r.json()
            if not recommendations.get("recommendations") or not recommendations["recommendations"][0]:
                await interaction.response.send_message("Sorry, no recommendations found, enter the command again!.",ephemeral=True)
                return

            title = recommendations["recommendations"][0][0]["title"]

            embed = discord.Embed(
                title="Your Recommendations",
                description=title,
                color=discord.Color.blue()
            )
            
            print("big butts", recommendations)
            view = Menu(interaction.user.id, recommendations["recommendations"][0][0]["id"])
            view.add_item(discord.ui.Button(label="anischedule.net", style=discord.ButtonStyle.link, url="https://anischedule.net/"))
        
            await interaction.response.send_message(f"Hey {interaction.user.mention}! Here are your recommendations Below",
        ephemeral=True, view=view, embed=embed)  

class Menu(discord.ui.View):
    def __init__(self, discord_id: int, anime_id: int):
        super().__init__()
        self.discord_id = discord_id
        self.anime_id = anime_id
        
    @discord.ui.button(label="Set Watching", style=discord.ButtonStyle.green)
    async def menu3(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:5000/api/currently_watching/?discord_id={self.discord_id}&anime_id={self.anime_id}") as r:

                await interaction.response.send_message("Added To Watchlist")                
                    
    @discord.ui.button(label="Set Completed", style=discord.ButtonStyle.green)
    async def menu2(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:5000/api/add_to_completed/?discord_id={self.discord_id}&anime_id={self.anime_id}") as r:

                await interaction.response.send_message("Added To Watchlist")    
        
    @discord.ui.button(label="Next Recommendation", style=discord.ButtonStyle.green)
    async def menu1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()  
        async with aiohttp.ClientSession() as session:
            async with session.get(f"http://127.0.0.1:5000/api/recommendations?discord_id={self.discord_id}") as r:
                recommendations = await r.json()
                first_recommendation = recommendations["recommendations"][0][0]
                first_title = first_recommendation["title"]
                first_id = first_recommendation["id"]
                embed = discord.Embed(
                    title="Your Next Recommendations",
                    description=first_title,
                    color=discord.Color.blue()
                )

                self.anime_id = first_id


                await interaction.edit_original_response(embed=embed) 
                    
                    
    
                
                
    
    
@bot.tree.command(name="say")
@app_commands.describe(thing_to_say = "What should I say?")
async def say (interaction: discord.Interaction, thing_to_say: str):
    await interaction.response.send_message(f"{interaction.user.name} said: `{thing_to_say}`")
   

   

@tasks.loop(hours=24)
async def fetch_and_send_schedule():
    for guild in bot.guilds:
        system_channel = guild.system_channel 
        if system_channel and system_channel.permissions_for(guild.me).send_messages:
            today_shows = await fetch_schedule()
            if today_shows:
                await send_schedule_with_embeds(today_shows, system_channel)
            else:
                await system_channel.send("No shows airing today!")

async def fetch_schedule():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://anischedule.net/api/seasonal/FALL") as response:
                if response.status == 200:
                    schedule_data = await response.json()
                    print(f"Fetched schedule data: {schedule_data}")
                    return filter_shows_for_today(schedule_data)
                else:
                    print(f"Failed to fetch schedule: HTTP {response.status}")
                    return []
        except Exception as e:
            print(f"Error fetching schedule: {e}")
            return []

async def send_schedule_with_embeds(shows: list, channel: discord.TextChannel) -> None:
    current_datetime = datetime.now().astimezone()
    current_day = current_datetime.strftime('%A, %b %d, %Y')

    embed = discord.Embed(
        title=f"📅 {current_day} - Today's Anime Schedule",
        description="Here are the shows airing today:",
        color=discord.Color.blue()
    )
    embed.set_footer(text="Data provided by anischedule.net")

    for anime in shows:
        title = anime.get('title_english') or anime.get('title_romaji', 'Unknown Title')
        airing_time = anime.get('nextAiringEpisode_airingAt')
        episode = anime.get('nextAiringEpisode_episode', 'Unknown')
        episodes = anime.get('episodes', None)

        episode_status = f"• **Episode Aired Today:** {episode + 2}"

        if airing_time:
            airing_datetime = datetime.fromtimestamp(airing_time, timezone.utc)
            days_difference = (airing_datetime - datetime.now(timezone.utc)).days

            if days_difference > 0 and days_difference <= 7:
                episode_status = "• **Coming Next Week**"

        airing_time_local = convert_timestamp_to_local_time(airing_time) if airing_time else "Unknown Time"

        show_details = (
            f"{episode_status}\n"
            f"• **Airing Time:** {airing_time_local}\n"
            f"• **Season:** {anime.get('season', 'Unknown')} {anime.get('year', 'Unknown')}"
        )

        if episodes is not None:
            show_details = f"• **Episodes:** {episodes}\n" + show_details

        embed.add_field(
            name=f"🎥 **{title}**",
            value=show_details,
            inline=False
        )

    try:
        await channel.send(embed=embed)
    except Exception as e:
        print(f"Failed to send message in channel {channel.name}: {e}")

def convert_timestamp_to_local_time(timestamp: int) -> str:
    try:
        local_time = datetime.fromtimestamp(timestamp).astimezone()
        return local_time.strftime('%I:%M %p %Z') 
    except (TypeError, ValueError):
        return "Invalid or missing time"

def filter_shows_for_today(schedule_data):
    today = datetime.now().weekday() 
    now = datetime.now(timezone.utc) 
    today_shows = []

    for anime in schedule_data:
        airing_time = anime.get('nextAiringEpisode_airingAt', None)
        if airing_time:
            airing_datetime = datetime.fromtimestamp(airing_time, timezone.utc)
            
            if airing_datetime.weekday() == today:
                today_shows.append(anime)

    return today_shows

def main() -> None:
    bot.run(TOKEN)  

if __name__ == '__main__':
    main()
