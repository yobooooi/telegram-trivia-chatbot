import logging
import prettytable as pt

from tinydb import (
    TinyDB,
    Query,
)

from tinydb.operations import increment


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


class UserStats:
    def __init__(self, chat_id) -> None:
        self.db = TinyDB(f'chatdbs/{chat_id}.json')

    def migrations(self):
        """migration function to align db schema"""
        all_records = self.db.all()
        for record in all_records:
            user_name = record['user_name']
            self.db.update(
                {
                    'current_round': 0,
                    'rounds_won': 0
                },
                Query().user_name == user_name
            )

        logger.info("migrations completed")

    def score_user(self, user_name, category_name, correct):
        """Update user scores"""
        record = self.db.get(Query().user_name == user_name)
        if record is not None and correct is True:
            logger.info(f"{user_name} answered correctly. updating scores")

            # updating new score and total_answered
            updated_score = record.get('score') + 1
            updated_total_answered = record.get('total_answered') + 1
            current_round = record.get('total_answered') + 1
            # update category scores and winning percentage
            categories = record.get('categories', {})
            if category_name in categories:
                # Category exists, update the score for the category
                categories[category_name] += 1
            else:
                # Category doesn't exist, add it with the score
                categories[category_name] = 1
            
            winning_percentage = round(100*(updated_score/updated_total_answered), 2)
            self.db.update(
                {
                    'categories': categories,
                    'winning_percentage': winning_percentage,
                    'score': updated_score,
                    'total_answered': updated_total_answered,
                    'current_round': current_round
                },
                Query().user_name == user_name
            )
        elif record is not None and correct is False:
            logger.info(f"{user_name} answered incorrectly")

            total_answered = record.get('total_answered') + 1
            winning_percentage = round(100*(record.get('score')/total_answered), 2)
            self.db.update(
                {
                    'total_answered': total_answered,
                    'winning_percentage': winning_percentage
                },
                Query().user_name == user_name
            )
        elif record is None and correct is True:
            if correct is True and self.db.get(Query().user_name == user_name) is None:
                logger.info(f"{user_name} doesn't exist and answered correctly adding 1 point to score")
                self.db.insert({
                    'user_name': user_name,
                    'score': 1,
                    'total_answered': 1,
                    'winning_percentage': 100,
                    'categories': {category_name: 1},
                    'current_round': 1,
                    'rounds_won': 0
                })
        else:
            self.db.insert({
                'user_name': user_name,
                'score': 0,
                'total_answered': 1,
                'winning_percentage': 0,
                'categories': {},
                'current_round': 1,
                'rounds_won': 0
            })
        logger.debug(self.db.all())
    
    def scores(self):
        """Return all user scores"""
        # Retrieve all records
        all_records = self.db.all()

        # Sort the records based on the specified column
        sorted_records = sorted(all_records, key=lambda x: x.get('current_round', 0), reverse=True)

        # Process each record and keep only the highest category
        for record in sorted_records:
            categories = record.get('categories', {})
            if categories:
                highest_category = max(categories, key=categories.get)
                record['best_category'] = highest_category
            else:
                record['best_category'] = None

        # Display or use the modified records
        logger.debug(sorted_records)
        return sorted_records

    def stats(self, user_name):
        record = self.db.get(Query().user_name == user_name)
        if record is not None:
            categories = record.get('categories', {})
            if categories:
                highest_category = max(categories, key=categories.get)
                record['best_category'] = highest_category
            else:
                record['best_category'] = None
        logger.debug(record)
        return record

    def reset_score(self, user_name):
        self.db.update(
            {
                'current_round': 0
            },
            Query().user_name == user_name
        )   
    
    def close_round(self):
        """Return winners and reset scores for current round"""
        # Retrieve all records
        all_records = self.db.all()
        sorted_records = sorted(all_records, key=lambda x: x.get('current_round', 0), reverse=True)

        # reset scores
        for record in all_records:
            user_name = record['user_name']
            self.reset_score(user_name)

        # allocate rounds_won point to winner
        winner_user_name = sorted_records[0]['user_name']
        logger.info(f"winner is {winner_user_name}")
        record = self.db.get(Query().user_name == winner_user_name)

        updated_rounds_won = record["rounds_won"] + 1
        self.db.update(
            {
                'rounds_won': updated_rounds_won
            },
            Query().user_name == winner_user_name
        )
        return winner_user_name