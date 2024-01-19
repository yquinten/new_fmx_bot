import os
import discord
import datetime
from dotenv import load_dotenv
from get_airline_data import AirlinesManager

load_dotenv()

guild_ids=[1045075821095817376]
bot = discord.Bot(intents=discord.Intents().all())

@bot.event
async def on_ready():
    print(f"{bot.user} is ready and connected to discord")
    tbt_files = await AirlinesManager(os.getenv('USERNAME'), os.getenv('PASSWORD')).get_tbt_files()
    guild = bot.get_guild(guild_ids[0])
    tbt_channel = guild.get_channel(1097829115719057579)
    today = datetime.date.today()
    tbt_thread = await tbt_channel.create_thread(name=f"Weekly TBT Data {today}", type = discord.ChannelType.public_thread, auto_archive_duration = 1440)
    for f in tbt_files:
        await tbt_thread.send(file=discord.File(f))
    print(f"{bot.user} finished its task and disconnects from discord now")
    await bot.close()

#bot.run(os.getenv('TBT_BOT_TOKEN'))