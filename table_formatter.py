from data_parser import table_type


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

                if not cell == line[-1]:
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

                if not cell == line[-1]:
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
    time_str = time_str.replace("–", " ").replace("-", " ")
    if "  " in time_str:
        time_str = " ".join(time_str.split())
    splited = time_str.split(" ")
    time_str = "-".join(spl.zfill(5) for spl in (splited[0], splited[-1]))
    return time_str


STYLES = {0: _style_0,
          1: _style_1}


def table_to_str(table: table_type,
                 date: str,
                 style_id: int = 0,
                 consider_column_width: bool = True) -> str:
    # Глубокое копирование для избежания внешнего изменения таблицы + форматирование
    table = [[cell if "http" in cell else cell.title() for cell in line] for line in table]

    for line in table[1:]:
        line[0] = _reformat_time_str(line[0])

    if table[0][1]:
        table[0][1] = f"{table[0][1]} Группа"

    column_width = _column_width_by_table(table) if consider_column_width else [0 for _ in range(len(table[0]))]

    table_str = STYLES.get(style_id, _style_0)(table, column_width)

    table_str = f"{date}\n{table_str}"

    if table_str.count("\n") <= 2:
        table_str = f"{table_str}Пар нет\n"

    return table_str


def tables_to_group_names(tables: list[table_type]) -> list[str]:
    return [table[0][1] for table in tables]


if __name__ == '__main__':
    tabl = [["ЧАС", "123", "КАБ"],
            ["1:02-02:04 2:05-03:04", "ПАРА1", "11"],
            ["12:03–13:05  13:16-14:05", "ПАРА2", "12"],
            ["13:04-14:26 14:34-15:06", "ПАРА3", "13"]]

    print(table_to_str(table=tabl,
                       style_id=0,
                       date="10.07.2022",
                       consider_column_width=True))
