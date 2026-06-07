import os
import discord
from discord.ext import commands

# インテント（権限）の設定
intents = discord.Intents.default()
intents.message_content = True

# ボットのオブジェクトを作成
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"ログインしました: {bot.user.name}")

@bot.command()
async def ping(ctx):
    await ctx.send("pong!")

# Renderなどの環境変数からトークンを読み込む
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("エラー: 環境変数 DISCORD_TOKEN が設定されていません。")
