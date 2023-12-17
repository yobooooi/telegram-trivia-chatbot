#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that works with polls. Only 3 people are allowed to interact with each
poll/quiz the bot generates. The preview command generates a closed poll/quiz, exactly like the
one the user sends the bot
"""
import logging
import time
import random

from telegram import (
    Poll,
    Update,
)

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PollAnswerHandler,
)

from src.trivia import (
    Trivia,
    Difficulty,
    Category
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


TOTAL_VOTER_COUNT = 4
API_TOKEN = "6824247146:AAFsZU42xQ0-w62YYcp4ddsa8SbrYg4YRdI"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Inform user about what this bot can do"""
    await update.message.reply_text(
        "Please select /poll to get a Poll, /quiz to get a Quiz or /preview"
        " to generate a preview for your poll"
    )


async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a predefined poll"""
    trivia = Trivia()
    for i in range(2):
        time.sleep(3)
        quiz_info = trivia.get_next_question(
            category_name   = random.choice(list(Category)).value,
            difficulty_name = random.choice(list(Difficulty)).value
        )

        message = await update.effective_message.reply_poll(
            "[{0}][{1}] - {2}".format(quiz_info["difficulty"].upper() ,quiz_info["category"].upper() ,quiz_info["question"]),
            quiz_info["answers"],
            type=Poll.QUIZ,
            correct_option_id=int(quiz_info["correct_answer_index"]),
            is_anonymous=False
        )
        # Save some info about the poll the bot_data for later use in receive_quiz_answer
        payload = {
            message.poll.id: {
                "chat_id": update.effective_chat.id, 
                "message_id": message.message_id,
                "correct_option_id":int(quiz_info["correct_answer_index"]),
            }
        }
        context.bot_data.update(payload)


async def receive_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close quiz after three participants took it"""
    # the bot can receive closed poll updates we don't care about
    poll_answer = update.poll_answer
    logger.info(poll_answer)
    payload = context.bot_data[poll_answer.poll_id]
    logger.info(payload)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("Use /quiz, /poll or /preview to test this bot.")


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(PollAnswerHandler(receive_quiz_answer))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

