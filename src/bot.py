#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""
Basic example for a bot that works with polls. Only 3 people are allowed to interact with each
poll/quiz the bot generates. The preview command generates a closed poll/quiz, exactly like the
one the user sends the bot
"""
import logging
import random
import prettytable as pt
import os

from telegram import (
    Poll,
    Update
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

from src.models import (
    UserStats
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

API_TOKEN = os.getenv("TELEGRAM_API_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a job to the queue."""
    chat_id = update.effective_message.chat_id
    try:
        # args[0] should contain the time for the timer in minutes
        interval = float(context.args[0])
        if interval < 0:
            await update.effective_message.reply_text("Sorry interval needs to be greater than 0!")
            return

        job_removed = remove_job_if_exists(str(chat_id), context)
        context.job_queue.run_repeating(
            quiz,
            interval=(interval*60), # multiply by 60 for minute representation
            chat_id=chat_id,
            name=str(chat_id),
        )

        text = f"Quiz successfully started. Question frequency set to every {int(interval)} minute(s)!"
        if job_removed:
            text += "Old one was removed."
        await update.effective_message.reply_text(text)

    except (IndexError, ValueError):
        await update.effective_message.reply_text("Usage: /quiz <minutes>")


async def unset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = "Quiz successfully cancelled!" if job_removed else "You have no active quiz."
    await update.message.reply_text(text)


def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True


async def quiz(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a predefined poll"""
    trivia    = Trivia()
    quiz_info = trivia.get_next_question(
        category_name   = random.choice(list(Category)).value,
        difficulty_name = random.choice(list(Difficulty)).value
    )

    job = context.job
    message = await context.bot.send_poll(
        chat_id=job.chat_id,
        question="[{0}][{1}] - {2}".format(quiz_info["difficulty"].upper() ,quiz_info["category"].upper() ,quiz_info["question"]),
        options=quiz_info["answers"],
        type=Poll.QUIZ,
        correct_option_id=int(quiz_info["correct_answer_index"]),
        is_anonymous=False,
        pool_timeout=3600 #TODO: use the quiz handler to set this value
    )
    # Save some info about the poll the bot_data for later use in receive_quiz_answer
    payload = {
        message.poll.id: {
            "chat_id": job.chat_id, 
            "message_id": message.message_id,
            "correct_option_id":int(quiz_info["correct_answer_index"]),
            "catergory": quiz_info["category"]
        }
    }
    context.bot_data.update(payload)


async def receive_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Close quiz after three participants took it"""

    poll_answer = update.poll_answer
    payload     = context.bot_data[poll_answer.poll_id]

    chat_id        = payload["chat_id"]
    user           = poll_answer.user
    user_answer    = poll_answer.option_ids[0]
    correct_answer = payload["correct_option_id"]
    catergory      = payload["catergory"]

    logger.info(f"chat_id: {chat_id}")
    logger.info(f"user: {user.username}")
    logger.info(f"user_answer: {user_answer}")
    logger.info(f"correct_answer: {correct_answer}")

    chat_user_stats = UserStats(chat_id=chat_id)
    # checking if answer is correct
    if int(user_answer) == int(correct_answer):
        chat_user_stats.score_user(
            user_name=user.username,
            category_name=catergory,
            correct=True
        )
    else:
        chat_user_stats.score_user(
            user_name=user.username,
            category_name=catergory,
            correct=False
        )


async def score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows scores"""
    chat_id     = update.message.chat_id
    quiz_scores = UserStats(chat_id=chat_id).scores()

    table = pt.PrettyTable(['username', 'score', 'win%'])
    table.align['username'] = 'l'
    table.align['score']  = 'c'
    table.align['win%']  = 'c'

    for score in quiz_scores:
        table.add_row([score['user_name'], score['score'], score['winning_percentage']])

    logger.info(table)
    await update.message.reply_text(f'```{table}```', parse_mode="MarkdownV2")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows stats for user"""

    chat_id  = update.message.chat_id
    username = update.message.from_user.username
    logger.info(f"{username} requesting stats for chat_id: {chat_id}")
    record   = UserStats(chat_id=chat_id).stats(user_name=username)

    table = pt.PrettyTable(["attribute", "value"])

    table.add_row(["user_name", record['user_name']])
    table.add_row(["score", record['score']])
    table.add_row(["tot_ans", record['total_answered']])
    table.add_row(["win%", record['winning_percentage']])
    table.add_row(["best_category", record['best_category']])

    logger.info(table)
    await update.message.reply_text(f'```{table}```', parse_mode="MarkdownV2")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("Use /quiz, /score to use this bot. Use /unset to stop quiz. Use /stats to see your personalized stats")


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("quiz", start))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("unset", unset))
    application.add_handler(CommandHandler("score", score))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(PollAnswerHandler(receive_quiz_answer))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

