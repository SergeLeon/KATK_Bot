from unittest import TestCase

from table_formatter import normalize_group_name, is_group_name, table_to_str


class Test(TestCase):
    def test_table_to_str(self):
        table = [
            ["ЧАС", "123", "КАБ"],
            ["1:02-02:04 2:05-03:04", "ПАРА1", "11"],
            ["12:03–13:05  13:16-14:05", "ПАРА2", "12"],
            ["13:04-14:26 14:34-15:06", "ПАРА3", "13"]
        ]
        date = "10.07.2022"
        must_output = """10.07.2022
123 Группа          | Каб
01:02-03:04 | Пара1 | 11
12:03-14:05 | Пара2 | 12
13:04-15:06 | Пара3 | 13
"""

        output = table_to_str(
            table=table,
            style_id=0,
            date=date,
            consider_column_width=True
        )

        self.assertEqual(output, must_output)

    def test_is_group_name(self):
        for i in ["20-ТО-1", "20ТО-1", "20-ТО1", "20ТО1", "20 ТО 1"]:
            self.assertTrue(is_group_name(i))

        for i in ["qwerty", "NOTAGROUPNAME"]:
            self.assertFalse(is_group_name(i))

    def test_normalize_group_name(self):
        for i in ["20ТО1", "20ТО-1", "20-ТО1", "20....,\\;:    ТО   1"]:
            self.assertEqual(normalize_group_name(i), "20-ТО-1")
