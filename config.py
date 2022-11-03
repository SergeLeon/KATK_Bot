import os

VERSION = "1.2.7"

VK_TOKEN = os.environ.get('VK_TOKEN')

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

URL = "http://katt44.ru/index.php?option=com_content&view=article&id=252&Itemid=129"

REGULAR_TIMETABLE_PATH = os.environ.get('REGULAR_TIMETABLE_PATH')

# Периодичность проверки изменений на сайте в секундах
CHECK_TIME = 240

table_type = list[list[str]]  # Временно вынесен в config
