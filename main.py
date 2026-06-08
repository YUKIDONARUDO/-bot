import os
import json
import threading  # Flaskを別スレッドで動かすために追加
import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask, request
import requests

TOKEN = os.getenv("DISCORD_TOKEN")

# --- Flask（OAuth2認証）の設定 ---
app = Flask(__name__)

CLIENT_ID = 'YOUR_CLIENT_ID'
CLIENT_SECRET = 'YOUR_CLIENT_SECRET'
REDIRECT_URI = 'YOUR_CALLBACK_URL'
TARGET_GUILD_ID = '確認したいサーバーID'
REQUIRED_ROLE_ID = '必要なロールID'

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "エラー: codeがありません。"
    
    # 1. アクセストークンの取得
    data = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': REDIRECT_URI
    }
    token_res = requests.post('https://discord.com/api/oauth2/token', data=data)
    token = token_res.json().get('access_token')

    if not token:
        return "エラー: アクセストークンの取得に失敗しました。"

    # 2. サーバー内のメンバー情報取得
    headers = {'Authorization': f'Bearer {token}'}
    member_res = requests.get(
        f'https://discord.com/api/v10/users/@me/guilds/{TARGET_GUILD_ID}/member', 
        headers=headers
    )
    
    # 3. ロール判定
    if member_res.status_code == 200:
        member_data = member_res.json()
        if REQUIRED_ROLE_ID in member_data.get('roles', []):
            return "認証成功：指定のロールを持っています！"
        else:
            return "認証成功：ロールを持っていません。"
    else:
        return "サーバーメンバー情報の取得に失敗しました（サーバーに参加していない可能性があります）。"

def run_flask():
    # 外部からのアクセスを受け付けるために 0.0.0.0 で起動 (ポートは環境に合わせて変更してください)
    app.run(host="0.0.0.0", port=5000)


# --- データベース代わりの簡易JSON管理関数 ---
DB_FILE = "ticket.json"

def db_get(filename, guild_id, default=None):
    if default is None:
        default = {}
    if not os.path.exists(filename):
        return default
    with open(filename, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data.get(str(guild_id), default)
        except json.JSONDecodeError:
            return default

def db_set(filename, guild_id, value):
    data = {}
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                pass
    data[str(guild_id)] = value
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# --- チケット機能のViewクラス ---
class TicketCreateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="チケットを開く", style=discord.ButtonStyle.primary, custom_id="ticket_create")
    async def create(self, interaction: discord.Interaction, button: discord.ui.Button):
        config = db_get(DB_FILE, interaction.guild.id, {})
        category = interaction.guild.get_channel(int(config["category_id"])) if config.get("category_id") else None
        
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        
        for role in interaction.guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        ch = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        
        embed = discord.Embed(title="チケット", description="用件を記入してください。", color=0x7c3aed)
        await ch.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"作成しました: {ch.mention}", ephemeral=True)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="チケットを閉じる", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()


# --- Botの初期設定 ---
intents = discord.Intents.default()
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

# サーバー環境で確実に常時待機させるためのsetup_hook定義
async def custom_setup_hook():
    bot.add_view(TicketCreateView())
    bot.add_view(TicketCloseView())
bot.setup_hook = custom_setup_hook


@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} 起動完了")

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"{bot.user} 起動完了")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.channel.id != 1513112875877797928:
        return

    if "猫缶" in message.content:
        await message.channel.send("猫缶のアドレスまで解説、事前準備[検索範囲は「OFF」typeはI32に設定]手順①32400で検索resultの1番上をview②8352と書かれたアドレスが見えるまで上にスクロールそのアドレスの上に大きい数が3つ並んだアドレスの上2つが猫缶に関するアドレスです。*上が自由、下が0固定")

    await bot.process_commands(message)


# --- スラッシュコマンド ---
@bot.tree.command(name="ping", description="応答確認")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("大丈夫！やれます！")

@bot.tree.command(name="チケット設置", description="チケットパネル設置")
@app_commands.default_permissions(administrator=True)
async def ticket_setup(interaction: discord.Interaction, category: discord.CategoryChannel = None):
    db_set(DB_FILE, interaction.guild_id, {"category_id": category.id if category else None})
    
    embed = discord.Embed(title="サポートチケット", description="下のボタンを押すと専用のチケットチャンネルが作成されます。", color=0xc026d3)
    await interaction.channel.send(embed=embed, view=TicketCreateView())
    await interaction.response.send_message("設置しました。", ephemeral=True)


if __name__ == "__main__":
    # Flaskを別スレッドで起動
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Discord Botを起動
    bot.run(TOKEN)
