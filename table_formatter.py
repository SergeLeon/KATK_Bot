import re
from random import randint

from config import table_type, table_dict_type


def _style_0(table: table_type, column_width: list[int]) -> str:
    """
    123 Группа          | Каб
    01:02-03:04 | Пара1 | 11
    12:03-14:05 | Пара2 | 12
    13:04-15:06 | Пара3 | 13
    """
    table_str = ""
    for line_num, line in enumerate(table):
        for cell_num, cell in enumerate(line):

            if not (line_num == 0 and cell_num == 0):
                if line_num == 0 and cell_num == 1:
                    table_str += cell.ljust((column_width[cell_num] + column_width[cell_num - 1] + 3), " ")
                else:
                    table_str += cell.ljust(column_width[cell_num], " ")

                if cell != line[-1]:
                    table_str += " | "

        table_str += "\n"
    return table_str


def _style_1(table: table_type, column_width: list[int]) -> str:
    """
    123 Группа | Каб
    1 | Пара1 | 11
    2 | Пара2 | 12
    3 | Пара3 | 13
    """
    table_str = ""
    for line_num, line in enumerate(table):
        for cell_num, cell in enumerate(line):

            if not (line_num == 0 and cell_num == 0):
                if cell_num == 0:
                    table_str += str(line_num)

                elif line_num == 0 and cell_num == 1:
                    table_str += cell.ljust((column_width[cell_num] + 4), " ")

                else:
                    table_str += cell.ljust(column_width[cell_num], " ")

                if cell != line[-1]:
                    table_str += " | "

        table_str += "\n"
    return table_str


def _style_2(table: table_type, column_width: list[int]) -> str:
    """
    123 Группа              | Каб
    1 | 01:02-03:04 | Пара1 | 11
    2 | 12:03-14:05 | Пара2 | 12
    3 | 13:04-15:06 | Пара3 | 13
    """
    table_str = ""
    for line_num, line in enumerate(table):
        for cell_num, cell in enumerate(line):

            if not (line_num == 0 and cell_num == 0):
                if cell_num == 0:
                    table_str += f"{line_num} | "

                if line_num == 0 and cell_num == 1:
                    table_str += cell.ljust((column_width[cell_num] + column_width[cell_num - 1] + 7), " ")
                else:
                    table_str += cell.ljust(column_width[cell_num], " ")

                if cell != line[-1]:
                    table_str += " | "

        table_str += "\n"
    return table_str


def _column_width_by_table(table: table_type) -> list:
    column_width = []
    for column in range(len(table[0])):
        max_width = 0
        for line in table[1:]:
            width = len(line[column])
            if width > max_width:
                max_width = width
        column_width.append(max_width)
    return column_width


def _reformat_time_str(time_str: str) -> str:
    """
    '8:30-9:15 9:20-10:05' >>> '08:30-10:05'
    """
    if len(time_str) > 8:
        time_str = time_str.replace(" ", "").replace("–", " ").replace("-", " ")
        if "  " in time_str:
            time_str = " ".join(time_str.split())
        splited = time_str.split(" ")
        time_str = "-".join(spl.zfill(5) for spl in (splited[0], splited[-1]))
    return time_str


STYLES = {0: _style_0,
          1: _style_1,
          2: _style_2, }


def table_to_str(table: table_type,
                 date: str,
                 style_id: int = 0,
                 consider_column_width: bool = True) -> str:
    # Глубокое копирование для избежания внешнего изменения таблицы + форматирование
    table = [[cell if "http" in cell else cell.title() for cell in line] for line in table]

    for line in table[1:]:
        if line[0]:
            line[0] = _reformat_time_str(line[0])

    if table[0][1]:
        table[0][1] = f"{table[0][1]} Группа"

    column_width = _column_width_by_table(table) if consider_column_width else [0 for _ in range(len(table[0]))]

    if (len(table) == 4 and
            randint(1, 50) == 12 and
            "Практика" == table[1][1] == table[2][1] == table[3][1]):
        table[1][1] += "??"
        table[2][1] += "!?"
        table[3][1] += "!!"

    table_str = STYLES.get(style_id, _style_0)(table, column_width)

    if "12.11" in date:
        date = f"🎂{date}🎂"

    elif ".12." in date:
        date = f"🎄{date}🎄"

    table_str = f"{date}\n{table_str}"

    if table_str.count("\n") <= 2:
        table_str = f"{table_str}Пар нет\n"

    return table_str


def tables_to_group_names(tables: list[table_type]) -> list[str]:
    return [table[0][1] for table in tables]


def tables_dict_to_group_names(tables_dict: table_dict_type) -> list[str]:
    group_names = set()

    for tables in tables_dict.values():
        for table in tables.values():
            group_names.add(table[0][1])

    return list(group_names)


def tables_to_tables_dict(tables: list[table_type]) -> dict[str, table_type]:
    return {table[0][1]: table for table in tables}


def is_group_name(string: str) -> bool:
    return bool(re.match(r"[1-9]{1,3}.{1,3}[1-9]{1,3}", string, re.IGNORECASE))


def normalize_group_name(group_name: str) -> str:
    # 20ТО1 20ТО-1 20-ТО1 >>> 20-ТО-1
    if group_name:
        first_char = group_name[0]
        group_name_parts = [first_char, ]
        last_is_numeric = first_char.isnumeric()
    else:
        return ""

    for char in group_name[1:]:
        if char.isalnum():
            if (last_is_numeric and char.isnumeric()) or (not last_is_numeric and char.isalpha()):
                group_name_parts[-1] += char
            else:
                group_name_parts.append(char)
            last_is_numeric = char.isnumeric()

    return "-".join(group_name_parts)


def surface_translit(string: str) -> str:
    eng_letters = "ABCEHKMOPTXY"
    rus_letters = "АВСЕНКМОРТХУ"
    trans_table = string.maketrans(eng_letters, rus_letters)
    return string.translate(trans_table)


def prepare_group_name(group_name: str) -> str:
    normalized_group = normalize_group_name(group_name)
    normalized_group = surface_translit(normalized_group)
    return normalized_group


if __name__ == '__main__':
    tabl = [["ЧАС", "123", "КАБ"],
            ["1:02-02:04 2:05-03:04", "ПАРА1", "11"],
            ["12:03–13:05  13:16-14:05", "ПАРА2", "12"],
            ["13:04-14:26 14:34-15:06", "ПАРА3", "13"]]

    print(table_to_str(table=tabl,
                       style_id=0,
                       date="10.07.2022",
                       consider_column_width=True))
