import os
from dotenv import load_dotenv
from cachetools import TTLCache
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from ffh_scraper import get_text_from_ffh, get_fpl_gameweeks
from agent import summarise_fpl_news

PROCESSED_UPDATES = TTLCache(maxsize=1000, ttl=300)  # Cache for 5 minutes


load_dotenv()


# Get bot token from environment variables
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

if not bot_token:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN not found in environment variables. Please set it in your .env file."
    )

# Create the Application
application = Application.builder().token(bot_token).build()


async def get_fpl_matthew(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /get-fpl-matthew command"""
    USER_ID = 102528399
    await update.message.reply_text(
        "Fetching Matthew's FPL team reveals... This may take a moment."
    )

    try:
        # Get gameweek information
        current_gw, next_gw, current_deadline, next_deadline = get_fpl_gameweeks()

        if not current_gw and not next_gw:
            await update.message.reply_text(
                "Error: Could not fetch gameweek information from FPL API."
            )
            return

        # Get text from Fantasy Football Hub
        hub_text = await get_text_from_ffh(update)

        if not hub_text:
            await update.message.reply_text(
                "Error: Could not extract text from Fantasy Football Hub page."
            )
            return

        # Summarize the FPL news
        summary = summarise_fpl_news(
            hub_text, current_gw, next_gw, current_deadline, next_deadline, USER_ID
        )

        # Send the summary (Telegram has a 4096 character limit per message)
        if len(summary) > 4096:
            # Split into chunks if too long
            chunks = [summary[i : i + 4096] for i in range(0, len(summary), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(summary)

    except Exception as e:
        await update.message.reply_text(f"An error occurred: {str(e)}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command"""
    await update.message.reply_text(
        "Welcome to the FPL Lab!\n\n"
        "Available commands:\n"
        "/get_fpl_matthew - Get Matthew's FPL team reveals and summary"
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle non-command messages"""
    await update.message.reply_text(
        "Press the /get_fpl_matthew command dumbass and you can get Matthew's FPL team reveals and summary."
    )


# def main() -> None:
#     """Start the bot"""
#     # Get bot token from environment variables
#     bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

#     if not bot_token:
#         raise ValueError(
#             "TELEGRAM_BOT_TOKEN not found in environment variables. Please set it in your .env file."
#         )

#     # Create the Application
#     application = Application.builder().token(bot_token).build()

#     # Register command handlers
#     application.add_handler(CommandHandler("start", start))
#     application.add_handler(CommandHandler("get_fpl_matthew", get_fpl_matthew))

#     # Register message handler for non-command messages
#     application.add_handler(
#         MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
#     )

#     # Run the bot
#     print("Bot is running...")
#     application.run_polling(allowed_updates=Update.ALL_TYPES)


# if __name__ == "__main__":
#     main()

# Register command handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("get_fpl_matthew", get_fpl_matthew))

# Register message handler for non-command messages
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))


# FastAPI app
@asynccontextmanager
async def lifespan(app: FastAPI):
    await application.initialize()
    yield
    await application.shutdown()


app = FastAPI(lifespan=lifespan)


# Webhook endpoint
@app.post("/webhook")
async def webhook(request: Request):
    update_data = await request.json()
    update = Update.de_json(update_data, application.bot)

    if update.update_id in PROCESSED_UPDATES:
        print(f"Duplicate update {update.update_id} skipped.")
        return Response(status_code=200)  # Acknowledge immediately to stop retries

    PROCESSED_UPDATES[update.update_id] = True  # Mark as processed

    await application.process_update(update)
    return Response(status_code=200)


# Health check for Render
@app.get("/")
async def health():
    return "Bot is running!"
