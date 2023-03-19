import os

VERSION = "1.3.0"

VK_TOKEN = os.environ.get('VK_TOKEN')

TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')

URL = "http://katt44.ru/index.php?option=com_content&view=article&id=252&Itemid=129"

REGULAR_TIMETABLE_PATH = os.environ.get('REGULAR_TIMETABLE_PATH')

# Периодичность проверки изменений на сайте в секундах
CHECK_TIME = 240

table_type = list[list[str]]  # Временно вынесен в config
group_name_type = str
date_type = str
table_dict_type = dict[
    date_type,
    dict[
        group_name_type,
        table_type
    ]
]
