import random
import string
import asyncio
import aiohttp
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔹 Telegram Bot Token
BOT_TOKEN = "7605916679:AAG8o4PNOCy0-TerrpCVBzQFcFcC7kL7NbU"

# 🔹 Admin ID
ADMIN_ID = 1386134836  

# 🔹 Mail.tm API URL
MAIL_API = "https://api.mail.tm"

# ✅ Store Generated Emails
user_emails = {}

# ✅ User Database (JSON File)
USER_DB = "users.json"

# ✅ Load Users Data
def load_users():
    try:
        with open(USER_DB, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# ✅ Save Users Data
def save_users(users):
    with open(USER_DB, "w") as file:
        json.dump(users, file, indent=4)

# ✅ Start Command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    users = load_users()

    if str(user.id) not in users:
        users[str(user.id)] = {
            "username": user.username if user.username else "N/A",
            "id": user.id
        }
        save_users(users)

        # ✅ Admin Notification
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"👤 **New User Joined!**\n\n👤 **Username:** @{user.username if user.username else 'N/A'}\n🆔 **User ID:** {user.id}\n📊 **Total Users:** {len(users)}"
        )

    # ✅ Welcome Message & Buttons
    keyboard = [
        [InlineKeyboardButton("📧 Generate Email", callback_data="generate_email")],
        [InlineKeyboardButton("🔗 Join", url="https://t.me/modverse_online")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_message = (
        "👋 Welcome to Temp Mail 💌!\n\n"
        "👉 Click on 🔗Join to use bot\n\n"
        "👉 Click on 📧 Generate Email and get new temp mail."
    )

    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

# ✅ Generate Email
async def generate_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = query.from_user.id
    random_email = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8)) + "@indigobook.com"
    email_password = "password123"
    payload = {"address": random_email, "password": email_password}

    async with aiohttp.ClientSession() as session:
        async with session.post(f"{MAIL_API}/accounts", json=payload) as response:
            data = await response.json()

            if "id" in data:
                async with session.post(f"{MAIL_API}/token", json={"address": random_email, "password": email_password}) as token_resp:
                    token_data = await token_resp.json()
                    auth_token = token_data.get("token")

                user_emails[user_id] = {"email": random_email, "token": auth_token, "last_message_id": None}

                # ✅ Send Response with Buttons
                keyboard = [
                    [
                        InlineKeyboardButton("📩 Check Inbox", callback_data="check_inbox"),
                        InlineKeyboardButton("📋 Copy Email", callback_data="copy_email")
                    ],
                    [InlineKeyboardButton("🔄 Generate New Mail", callback_data="generate_email")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.message.reply_text(f"✅ **Generated Email:**\n`{random_email}`", parse_mode="Markdown", reply_markup=reply_markup)
            else:
                await query.message.reply_text("❌ Email generate karne me error aayi!")

# ✅ Check Inbox
async def check_inbox(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    if user_id not in user_emails:
        await query.message.reply_text("❌ Pehle email generate karein!")
        return

    email_data = user_emails[user_id]
    headers = {"Authorization": f"Bearer {email_data['token']}"}

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{MAIL_API}/messages", headers=headers) as response:
            data = await response.json()

            if data.get("hydra:totalItems", 0) > 0:
                latest_message_id = data["hydra:member"][0]["id"]

                async with session.get(f"{MAIL_API}/messages/{latest_message_id}", headers=headers) as msg_response:
                    message_data = await msg_response.json()

                    sender = message_data.get("from", {}).get("address", "Unknown")
                    subject = message_data.get("subject", "No Subject")
                    body = message_data.get("text", "No Body")

                    message_text = f"📩 **New Email Received**\n\n**From:** `{sender}`\n**Subject:** `{subject}`\n\n📜 **Message:**\n```\n{body}\n```"
                    await query.message.reply_text(message_text, parse_mode="Markdown")
            else:
                await query.message.reply_text("📭 Inbox empty hai!")

# ✅ Auto Inbox Checker (Background Task)
async def auto_check_inbox(context: ContextTypes.DEFAULT_TYPE):
    for user_id, email_data in user_emails.items():
        headers = {"Authorization": f"Bearer {email_data['token']}"}

        async with aiohttp.ClientSession() as session:
            async with session.get(f"{MAIL_API}/messages", headers=headers) as response:
                data = await response.json()

                if data.get("hydra:totalItems", 0) > 0:
                    latest_message_id = data["hydra:member"][0]["id"]

                    if latest_message_id != email_data.get("last_message_id"):
                        async with session.get(f"{MAIL_API}/messages/{latest_message_id}", headers=headers) as msg_response:
                            message_data = await msg_response.json()

                            sender = message_data.get("from", {}).get("address", "Unknown")
                            subject = message_data.get("subject", "No Subject")
                            body = message_data.get("text", "No Body")

                            message_text = f"📩 **New Email Received**\n\n**From:** `{sender}`\n**Subject:** `{subject}`\n\n📜 **Message:**\n```\n{body}\n```"
                            await context.bot.send_message(chat_id=user_id, text=message_text, parse_mode="Markdown")

                            user_emails[user_id]["last_message_id"] = latest_message_id

# ✅ Button Handler
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "generate_email":
        await generate_email(update, context)
    elif query.data == "check_inbox":
        await check_inbox(update, context)
    elif query.data == "copy_email":
        user_id = query.from_user.id
        email = user_emails.get(user_id, {}).get("email", "No Email Found")
        await query.message.reply_text(f"📋 Copied: `{email}`", parse_mode="Markdown")

# ✅ Main Function
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    # 🔄 Every 10 seconds auto-check inbox
    job_queue = app.job_queue
    job_queue.run_repeating(auto_check_inbox, interval=10, first=10)

    print("🤖 Bot Started...")
    app.run_polling()

if __name__ == "__main__":
    main()
