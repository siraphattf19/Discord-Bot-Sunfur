import discord
from discord.ext import commands
from discord import app_commands
from user_logger import log_action, get_all_user_logs
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.all()
intents.message_content = True
intents.members = True
intents.voice_states = True
intents.guilds = True
intents.presences = True

bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ บอททำงานในชื่อ {bot.user}")
    activity = discord.Streaming(
        name="Youtube",
        url="https://youtu.be/fLexgOxsZu0?si=FDsmMCgM367IY6c0"
    )
    await bot.change_presence(status=discord.Status.online, activity=activity)

# คำสั่ง: /resume @user
@bot.tree.command(name="resume", description="ดูข้อมูลของผู้ใช้ในเซิร์ฟเวอร์")
@app_commands.describe(user="เลือกผู้ใช้ที่คุณต้องการดูข้อมูล")
async def resume(interaction: discord.Interaction, user: discord.Member):

    created = user.created_at.strftime("%d %b %Y %H:%M")
    joined = user.joined_at.strftime("%d %b %Y %H:%M") if user.joined_at else "N/A"
    roles = [role.mention for role in user.roles if role.name != "@everyone"]
    roles_text = ", ".join(roles) if roles else "ไม่มี Role อื่น"

    embed = discord.Embed(
        title=f"📄 ข้อมูลของ {user.display_name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="ชื่อบัญชี", value=f"{user} (`{user.id}`)", inline=False)
    embed.add_field(name="วันที่สร้างบัญชี", value=created, inline=True)
    embed.add_field(name="วันที่เข้าร่วมเซิร์ฟเวอร์", value=joined, inline=True)
    embed.add_field(name="Roles", value=roles_text, inline=False)

    await interaction.response.send_message(embed=embed,ephemeral=True)
    
@bot.event
async def on_message(message):
    if not message.author.bot:
        log_action(message.author.id, message.author.name, "message", message.content)
    await bot.process_commands(message)

@bot.event
async def on_member_join(member):
    log_action(member.id, member.name, "join", "เข้าร่วมเซิร์ฟเวอร์")

@bot.event
async def on_member_remove(member):
    log_action(member.id, member.name, "leave", "ออกจากเซิร์ฟเวอร์")

@bot.event
async def on_member_update(before, after):
    if before.nick != after.nick:
        try:
            async for entry in after.guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == after.id and entry.user.id != after.id:
                    log_action(after.id, after.name, "nickname_change",
                               f"ชื่อเล่นเปลี่ยนจาก '{before.nick}' → '{after.nick}' โดย {entry.user} (ID: {entry.user.id})")
                    break
        except Exception as e:
            print("ไม่สามารถตรวจสอบการเปลี่ยนชื่อเล่น:", e)
        else:
            log_action(after.id, after.name, "nickname_change",
                       f"ชื่อเล่นเปลี่ยนจาก '{before.nick}' → '{after.nick}'")

@bot.event
async def on_voice_state_update(member, before, after):
    guild = member.guild

    def log_channel_members(channel):
        if channel:
            members = [f"{m.name} (ID: {m.id})" for m in channel.members]
            return f"\n👥 ในห้องนี้มี {len(channel.members)} คน:\n" + "\n".join(members)
        return ""

    # เข้าห้องเสียงใหม่
    if before.channel is None and after.channel is not None:
        log_action(
            member.id, member.name, "voice_join",
            f"เข้าห้องเสียง {after.channel.name}" + log_channel_members(after.channel)
        )

    # ออกจากห้องเสียง
    elif before.channel is not None and after.channel is None:
        log_action(
            member.id, member.name, "voice_leave",
            f"ออกจากห้องเสียง {before.channel.name}" + log_channel_members(before.channel)
        )

    # ย้ายห้องเสียง
    elif before.channel != after.channel:
        moved_by_someone = False
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_move):
                if entry.target.id == member.id and entry.user.id != member.id:
                    log_action(member.id, member.name, "voice_moved_by_admin",
                               f"ถูกย้ายจาก {before.channel.name} ย้ายไปห้อง {after.channel.name} โดย {entry.user} (ID: {entry.user.id})"
                               + log_channel_members(after.channel))
                    moved_by_someone = True
                    break
        except Exception as e:
            print("ไม่สามารถตรวจสอบการย้ายห้อง:", e)

        if not moved_by_someone:
            log_action(
                member.id, member.name, "voice_move",
                f"ย้ายห้องจาก {before.channel.name} ย้ายไปห้อง {after.channel.name}" + log_channel_members(after.channel)
            )

    # ปิด/เปิดไมค์
    if before.self_mute != after.self_mute:
        action = "ปิดไมค์" if after.self_mute else "เปิดไมค์"
        log_action(member.id, member.name, "mute_toggle", action)

    # ปิด/เปิดหูฟัง
    if before.self_deaf != after.self_deaf:
        action = "ปิดหูฟัง" if after.self_deaf else "เปิดหูฟัง"
        log_action(member.id, member.name, "deaf_toggle", action)

    # ถูก mute/unmute โดยคนอื่น
    if before.mute != after.mute:
        action = "ถูก mute" if after.mute else "ถูก unmute"
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == member.id and entry.user.id != member.id:
                    action += f" โดยผู้ใช้ {entry.user} (ID: {entry.user.id})"
                    break
        except Exception as e:
            print("ไม่สามารถเข้าถึง audit log:", e)
        log_action(member.id, member.name, "moderated_mute", action)

    # ถูก deafen/undeafen โดยคนอื่น
    if before.deaf != after.deaf:
        action = "ถูก deafen" if after.deaf else "ถูก undeafen"
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_update):
                if entry.target.id == member.id and entry.user.id != member.id:
                    action += f" โดยผู้ใช้ {entry.user} (ID: {entry.user.id})"
                    break
        except Exception as e:
            print("ไม่สามารถเข้าถึง audit log:", e)
        log_action(member.id, member.name, "moderated_deaf", action)

    # ถูกเตะออกจากห้องเสียง
    if before.channel is not None and after.channel is None and not before.self_mute and not before.self_deaf:
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_disconnect):
                if entry.target.id == member.id:
                    log_action(
                        member.id, member.name, "disconnected",
                        f"ถูกตัดออกจากห้องเสียงโดย {entry.user} (ID: {entry.user.id})"
                    )
                    break
        except Exception as e:
            print("ไม่สามารถตรวจสอบการ disconnect:", e)

@bot.tree.command(name="logall", description="ดู log ทั้งหมดของผู้ใช้ (ใช้ชื่อ, @mention หรือ ID ได้)")
@app_commands.describe(query="ใส่ชื่อ, @mention หรือ ID ของผู้ใช้")
async def logall(interaction: discord.Interaction, query: str):
    await interaction.response.defer(ephemeral=True)

    user = None

    if query.startswith("<@") and query.endswith(">"):
        user_id = int(query.strip("<@!>"))
        user = await bot.fetch_user(user_id)
    else:
        try:
            user_id = int(query)
            user = await bot.fetch_user(user_id)
        except ValueError:
            if interaction.guild:
                for member in interaction.guild.members:
                    if query.lower() in (member.name.lower(), (member.nick or "").lower()):
                        user = member
                        break

    if not user:
        await interaction.followup.send("❌ ไม่พบผู้ใช้นั้น กรุณาใส่ชื่อ, mention หรือ ID ให้ถูกต้อง", ephemeral=True)
        return

    logs = get_all_user_logs(user.id)
    if not logs:
        await interaction.followup.send(f"❌ ไม่พบ log ของผู้ใช้ {user.name}", ephemeral=True)
        return

    log_lines = [
        f"🕒 `{log['timestamp']}`\n🔸 ประเภท: **{log['action_type']}**\n🔹 รายละเอียด: {log['detail']}"
        for log in logs[-10:]
    ]

    embed = discord.Embed(title=f"📜 Log ล่าสุดของ {user.name}", color=discord.Color.green())
    embed.description = "\n\n".join(log_lines)
    embed.set_footer(text=f"ทั้งหมด {len(logs)} รายการ (แสดงล่าสุด 10 รายการ)")

    await interaction.followup.send(embed=embed, ephemeral=True)

@bot.tree.command(name="join", description="ให้บอทเข้าห้องเสียงเดียวกับคุณ")
async def join(interaction: discord.Interaction):
    voice_state = interaction.user.voice

    if not voice_state or not voice_state.channel:
        await interaction.response.send_message(
            "❌ คุณต้องอยู่ในห้องเสียงก่อนถึงจะใช้คำสั่งนี้ได้",
            ephemeral=True
        )
        return

    channel = voice_state.channel

    # ตัดการเชื่อมต่อเดิม (ถ้ามี)
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()

    await channel.connect()
    await interaction.response.send_message(
        f"✅ เข้าห้องเสียง `{channel.name}` เรียบร้อยแล้ว",
        ephemeral=True
    )


@bot.tree.command(name="leave", description="ให้บอทออกจากห้องเสียง")
async def leave(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message(
            "👋 บอทออกจากห้องเสียงแล้ว",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "❌ บอทยังไม่ได้อยู่ในห้องเสียง",
            ephemeral=True
        )

# 🔐 ใส่ token ของคุณที่นี่
bot.run("MTM3ODQ0MjgyNjY5MzQ3NjM2Mg.GkVIUC.xhMgd1JkAzhSd8SrTdwBCXdg5McDFoAkpioL-k")
