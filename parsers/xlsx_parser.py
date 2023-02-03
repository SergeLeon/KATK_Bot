from openpyxl import load_workbook

from config import table_type


def _worksheet_as_list(worksheet, replace_none=True) -> list[list[str]]:
    table = []
    for row in worksheet.rows:
        if replace_none:
            table.append([cell.value.strip().replace("\n", "").upper() if cell.value else "" for cell in row])
        else:
            table.append([cell.value for cell in row])
    return table


def _expand_weekdays(table) -> None:
    last = ""
    for num, cell in enumerate(table[0]):
        if cell:
            last = cell
        else:
            table[0][num] = last


def _find_weekdays_slices(weekdays: list[str]) -> list:
    last_weekday = ""
    last_empty_cell = 0
    last_weekday_cell_num = 0

    slices = []
    for weekday_cell_num, weekday in enumerate(weekdays, 1):
        if not weekday:
            continue
        if weekday_cell_num != 1:
            last_empty_cell = weekday_cell_num - 1
            slices.append([last_weekday, last_weekday_cell_num, last_empty_cell])

        last_weekday = weekday
        last_weekday_cell_num = weekday_cell_num

    slices.append((last_weekday, last_weekday_cell_num, len(weekdays)))

    return slices


def _extract_timetables_by_weekdays(table):
    weekdays = table[0][1:]
    timestamps = table[1]

    weekdays_slices = _find_weekdays_slices(weekdays)

    timetables_by_weekdays = {}
    for weekday, _, _ in weekdays_slices:
        timetables_by_weekdays[weekday] = {}

    for num, row in enumerate(table[2:]):
        group_name = row[0].replace(" ", "-").replace("--", "-")
        for weekday, slice_start, slice_stop in weekdays_slices:
            timetables_by_weekdays[weekday][group_name] = (
                timestamps[slice_start:slice_stop+1], row[slice_start:slice_stop+1])

    return timetables_by_weekdays


def _format_timetable(timetable: list, group_name: str) -> table_type:
    table = [
        ["", group_name, ""],
    ]
    for pack in zip(*timetable):
        table.append([*pack, ""])
    return table


def _format_timetables_by_weekdays(timetables_by_weekdays: dict[str:dict[str:list]]) -> dict[str:list[table_type]]:
    tables_by_weekday = {}

    for weekday in timetables_by_weekdays.keys():
        tables_by_weekday[weekday] = []

    for weekday, timetables in timetables_by_weekdays.items():
        for group_name, timetable in timetables.items():
            tables_by_weekday[weekday].append(_format_timetable(timetable, group_name))

    return tables_by_weekday


def get_regular_timetables(filename: str) -> dict[str:list[table_type]]:
    wb = load_workbook(filename=filename, read_only=True)
    ws = wb.worksheets[0]
    table = _worksheet_as_list(ws)

    tables_by_weekday = _format_timetables_by_weekdays(_extract_timetables_by_weekdays(table))
    return tables_by_weekday


if __name__ == "__main__":
    from config import REGULAR_TIMETABLE_PATH
    from table_formatter import table_to_str
    timetables = get_regular_timetables(REGULAR_TIMETABLE_PATH)
    for weekday, tables in timetables.items():
        print(len(tables))
        for i in tables:
            print(table_to_str(i, date=weekday))
