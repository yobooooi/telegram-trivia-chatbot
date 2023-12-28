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

from tinydb import (
    TinyDB,
    Query,
)

from tinydb.operations import increment


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

API_TOKEN = "6824247146:AAFsZU42xQ0-w62YYcp4ddsa8SbrYg4YRdI"

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
        is_anonymous=False
    )
    # Save some info about the poll the bot_data for later use in receive_quiz_answer
    payload = {
        message.poll.id: {
            "chat_id": job.chat_id, 
            "message_id": message.message_id,
            "correct_option_id":int(quiz_info["correct_answer_index"]),
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

    logger.info(f"chat_id: {chat_id}")
    logger.info(f"user: {user.username}")
    logger.info(f"user_answer: {user_answer}")
    logger.info(f"correct_answer: {correct_answer}")
    
    db = TinyDB(f'{chat_id}.json')

    User = Query()
    # checking if answer is correct
    if int(user_answer) == int(correct_answer):
        # searching if user exists in database to increment score
        if db.get(User.user_name == user.username) is not None:
            logger.info(f"{user.username} answered correctly incrementing score")
            db.update(increment('score'), User.user_name == user.username)
        else:
            logger.info(f"{user.username} answered correctly adding 1 point to score")
            db.insert({ 
                'user_name': user.username,
                'score': 1
            })
    else:
        # searching if user exists in database to increment score to add user entry
        if db.get(User.user_name == user.username) is None:
            logger.info(f"{user.username} answered incorrectly. adding to score database")
            db.insert({ 
                'user_name': user.username,
                'score': 0
            })
    logger.debug(db.all())

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the job if the user changed their mind."""
    chat_id = update.message.chat_id
    db = TinyDB(f'{chat_id}.json')

    markdown_table = "| User Name      | Score |\n| -------------- | ----- |\n"
    for row in db.all():
        markdown_table += f"| {row['user_name']:<15} | {row['score']:<5} |\n"

    logger.info(markdown_table)
    await update.message.reply_text(markdown_table)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display a help message"""
    await update.message.reply_text("Use /quiz, /score to use this bot. Use /unset to stop quiz")


def main() -> None:
    """Run bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("quiz", start))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("unset", unset))
    application.add_handler(CommandHandler("score", score))
    application.add_handler(PollAnswerHandler(receive_quiz_answer))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

