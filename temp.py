from src import models
chat_id = "-4095437959"


chat_records = models.UserStats(chat_id=chat_id)
print(chat_records.close_round())