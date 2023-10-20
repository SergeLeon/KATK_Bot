from typing import Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup as bs
from bs4.element import Tag
from fake_useragent import UserAgent
from requests.exceptions import ReadTimeout, ConnectionError
from time import sleep

from config import table_type, table_dict_type
from table_formatter import tables_to_group_names, is_group_name, normalize_group_name, tables_to_tables_dict, \
    surface_translit
from parsers.xlsx_parser import get_regular_timetables

WEEKDAYS = ("понедельник", 'вторник', 'среда', 'четверг', 'пятница', 'суббота')
NUMBERS = "0123456789"


def _find_inclusion(string: str, inclusions: Iterable[str]) -> str:
    """
    Возвращает первое найденное в строке включение или пустую строку, если включений не найдено.
    """
    for inclusion in inclusions:
        if inclusion in string:
            return inclusion
    return ""


def _clear_str(string: str) -> str:
    string = string.replace("\n", " ")
    string = string.replace(u"\xa0", "")

    while "  " in string:
        string = string.replace("  ", " ")

    string = string.strip()

    return string


def _get_link(a: Tag, domain: str) -> str:
    link = a.get("href")
    if "http" not in link:
        link = f"http://{domain}{link}"
    return link


class Parser:
    def __init__(self, url: str, regular_timetable_path: str):
        self.ua = UserAgent()
        self.url = url
        self.domain = urlparse(self.url).netloc
        self.session = requests.Session()
        self.soup = bs()
        self.weekday = ""
        self.date = ""
        self.dates = []
        self.update()

        self.regular_timetable_path = regular_timetable_path
        self.regular_timetable = get_regular_timetables(self.regular_timetable_path) \
            if self.regular_timetable_path else {}
        self._clear_regular_timetable()

    def _clear_regular_timetable(self):
        for weekday, tables in self.regular_timetable.items():
            for num, table in enumerate(tables):
                table = self._delete_uninformative_table_lines(table)
                table = self._reformat_table(table)
                self.regular_timetable[weekday][num] = table

    def update(self, recon_max: int = 5, recon_time: int = 60, count: int = 1):
        try:
            headers = {'User-Agent': self.ua.random.strip()}
            self.session.headers.update(headers)

            response = self.session.get(self.url, timeout=5)
            content = response.content

            self.soup = bs(content, "html.parser")
            self._update_dates()
            self.weekday, self.date = self._get_last_date()

        except (ReadTimeout, ConnectionError):
            count += 1

            if count % (recon_max * 4) == 0:
                sleep(recon_time * 15)
            elif count % (recon_max * 2) == 0:
                sleep(recon_time * 10)
            elif count % recon_max == 0:
                sleep(recon_time)

            sleep(recon_time // 10)
            self.update(recon_max=recon_max, recon_time=recon_time, count=count)

    def _update_dates(self):
        strings = self._pars_spans_text()
        dates = []
        for string in strings:
            string = string.lower()
            if "змен" not in string:
                continue

            day = _find_inclusion(string, WEEKDAYS)
            if not day:
                continue

            texts_words = string.split()
            date = ""

            # Отделение строк с информацией
            for word in texts_words:
                if day in word or _find_inclusion(word, NUMBERS):
                    date += word

            weekday = day.upper()
            date = date.title()
            if _find_inclusion(date, NUMBERS):
                dates.append((weekday, date))

        self.dates = dates

    def _get_last_date(self):
        if not self.dates:
            return "", ""
        # TODO: Если сменится месяц то вернётся неверное значение
        dates = sorted(self.dates, key=lambda date: date[1])
        weekday, date = dates[-1]
        return weekday, date

    def get_date(self) -> str:
        return self.date

    def _get_cell_text(self, cell: Tag) -> str:
        text = cell.text.upper()

        text = _clear_str(text)

        text = text.replace(
            "ЭТОТ АДРЕС ЭЛЕКТРОННОЙ ПОЧТЫ ЗАЩИЩЕН ОТ СПАМ-БОТОВ. У ВАС ДОЛЖЕН БЫТЬ ВКЛЮЧЕН JAVASCRIPT ДЛЯ ПРОСМОТРА.",
            "ПОЧТА НА САЙТЕ.")

        # Поиск и вставка ссылки/ок
        cell_a = cell.find_all("a")
        if cell_a:
            for a in cell_a:
                link = _get_link(a=a, domain=self.domain)
                text += " " + link

        return text

    def _pars_today_tables(self) -> list[table_type]:
        parse_tables = self.soup.find_all("table")

        tables = []
        for table in parse_tables:
            text_lines = []
            lines = table.find_all("tr")

            for line in lines:
                cells = line.find_all("td")

                texts = [self._get_cell_text(cell) for cell in cells]

                if any(texts):
                    text_lines.append(texts)
            tables.append(text_lines)
        return tables

    def _select_last_table(self, tables: list[table_type]):
        for num, date in enumerate(self.dates):
            if date[1] == self.date:
                return tables[num]
        return tables[0]

    @staticmethod
    def _split_table_by_lines(text_table: table_type) -> list[table_type]:
        last_line = 0
        new_tables = []
        for line_num, line in enumerate(text_table):
            group_name_in_line = any(is_group_name(cell) for cell in line[1:])
            is_group_names_line = "ГРУПП" in line[0] or group_name_in_line
            if is_group_names_line:
                new_tables.append(text_table[last_line: line_num])
                last_line = line_num
        new_tables.append(text_table[last_line:])

        return new_tables[1:]

    @staticmethod
    def _split_tables_by_columns(tables: list[table_type]) -> list[table_type]:
        group_tables = []
        for table in tables:

            for group_num in range(1, len(table[0])):
                group_tables.append([[line[0], line[group_num]] for line in table])

        return group_tables

    def _split_table(self, table: table_type) -> list[table_type]:
        return self._split_tables_by_columns(
            self._split_table_by_lines(table))

    @staticmethod
    def _delete_uninformative_table_lines(table: table_type) -> table_type:
        table = [[cell for cell in line] for line in table]

        for line in table[::-1]:
            if line[1]:
                break
            table.remove(line)

        return table

    @staticmethod
    def _reformat_table(table: table_type) -> table_type:
        table = [[cell for cell in line] for line in table]

        for line in table:

            if len(line) != 2:
                continue

            titles = []
            additions = []
            if "http" in line[1]:
                splited = line[1].split()

                for word in splited:
                    if "http" in word:
                        additions.append(word)
                    else:
                        titles.append(word)

                line[1] = " ".join(titles)

            if "КАБ" in line[1]:
                splited = line[1].rsplit('КАБ', 1)

                title = splited[0].rstrip("( ")
                cabinet_number = splited[1].strip("). ")

                line[1] = title
                additions.insert(0, cabinet_number)

            line.append(" ".join(additions))

        group_name = table[0][1]
        group_name = group_name.replace("_", "-").replace(" ", "")

        if group_name.count("-") < 2:
            group_name = normalize_group_name(group_name)

        group_name = surface_translit(group_name)
        table[0][1] = group_name

        return table

    @staticmethod
    def _separate_group_table(table: table_type) -> list[table_type]:
        first_line = table[0][1].split()
        if len(first_line) <= 1:
            return [table, ]

        group_names = []
        rest = []

        for item in first_line:
            if is_group_name(item):
                group_names.append(item)
            elif (("-" in item or item.isnumeric()) or len(item) == 1) and group_names:
                group_names[-1] += item
            else:
                rest.append(item)

        # 20-ТО-1;2;3 >>> 20-TO-1, 20-TO-2, 20-TO-3
        for name in group_names:
            if ";" not in name:
                continue
            inclusions = name.split(";")

            group_names.remove(name)
            group_names.insert(0, inclusions[0])

            for inclusion in inclusions[1:]:
                base = inclusions[0].rsplit("-", 1)[0]
                group_names.append(f"{base}-{inclusion}")

        group_tables = []

        for group_name in group_names:
            group_table = [[cell for cell in line] for line in table]
            group_table[0][1] = group_name
            group_table[0].append(" ".join(rest))
            group_tables.append(group_table)

        return group_tables

    def _tables_to_group_tables(self, tables: list[table_type], weekday: str) -> list[table_type]:
        group_tables = []

        for table in tables:
            table = self._delete_uninformative_table_lines(table)

            if not table or not table[0][1]:
                continue

            if " " in table[0][1]:
                separated_tables = self._separate_group_table(table)

                if len(separated_tables) == 1:
                    table = separated_tables[0]
                elif len(separated_tables) > 1:
                    tables += separated_tables
                    continue

            table = self._reformat_table(table)
            group_tables.append(table)

        group_names = tables_to_group_names(group_tables)

        for regular_table in self.regular_timetable.get(weekday, ""):
            if regular_table[0][1] not in group_names:
                group_tables.append(regular_table)

        return group_tables

    def get_tables(self) -> table_dict_type:
        tables = self._pars_today_tables()
        dates = self.dates
        tables_dict = dict()

        for date_info, table in zip(dates, tables):
            weekday, date = date_info
            tables_dict[date] = tables_to_tables_dict(
                self._tables_to_group_tables(
                    tables=self._split_table(table), weekday=weekday))

        return tables_dict

    def _pars_spans_text(self) -> list:
        spans = self.soup.find_all("b")
        spans_text = [span.text for span in spans]
        return spans_text


if __name__ == '__main__':
    from utils import print_tables

    print_tables.main()
