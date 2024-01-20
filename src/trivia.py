import html
import json
import logging
import requests
import random


from enum import Enum

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Category(Enum):
    GENERAL_KNOWLEDGE = 9
    FILM = 11
    TELEVISION = 14
    VIDEO_GAMES = 15
    SCIENCE = 17
    MATHEMATICS = 19
    SPORTS = 21
    GEOGRAPHY = 22
    HISTORY = 23
    ART = 25
    VEHICLES = 28



class Trivia:
    def __init__(self) -> None:

        self.base_url = "https://opentdb.com/api.php"
        self.amount = 1

    def get_next_question(self, category_name: str, difficulty_name: str):
        request_params = {
            "amount": self.amount,
            "category": category_name,
            "difficulty": difficulty_name
        }
        response = requests.get(self.base_url, params=request_params)
        logger.debug(request_params)
        logger.debug(response.text)

        data = json.loads(response.text)["results"][0]
        logger.debug(data)
        
        answers = [
            html.unescape(answer) for answer in data["incorrect_answers"] 
        ]
        answers.append(html.unescape(data["correct_answer"]))
        random.shuffle(answers)
        logging.debug(answers)

        quiz = {
            "difficulty": html.unescape(data["difficulty"]),
            "category": html.unescape(data["category"]),
            "question": html.unescape(data["question"]),
            "correct_answer_index": answers.index(html.unescape(data["correct_answer"])),
            "answers": answers
        }
        logger.info(quiz)
        return quiz