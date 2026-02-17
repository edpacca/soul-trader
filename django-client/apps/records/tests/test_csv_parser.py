from datetime import date
from decimal import Decimal

from django.test import TestCase

from apps.records.services.csv_parser import DefaultCSVParser


class TestDefaultCSVParser(TestCase):
    def setUp(self):
        self.parser = DefaultCSVParser()

    def test_parse_valid_csv(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code,currency\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA,GBP\n"
            "2024-02-20,Widget B,5,12.00,60.00,4.00,EC1A 1BB,USD\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 2)
        self.assertEqual(len(errors), 0)
        self.assertEqual(records[0]["date"], date(2024, 1, 15))
        self.assertEqual(records[0]["item_name"], "Widget A")
        self.assertEqual(records[0]["quantity"], 10)
        self.assertEqual(records[0]["unit_price"], Decimal("5.00"))
        self.assertEqual(records[0]["total_price"], Decimal("50.00"))
        self.assertEqual(records[0]["shipping_cost"], Decimal("3.50"))
        self.assertEqual(records[0]["post_code"], "SW1A 1AA")
        self.assertEqual(records[0]["currency"], "GBP")

    def test_parse_default_currency(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["currency"], "GBP")

    def test_parse_date_formats(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "15/01/2024,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["date"], date(2024, 1, 15))

    def test_missing_required_columns(self):
        csv_content = "date,item_name,quantity\n2024-01-15,Widget,10\n"
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required columns", errors[0])

    def test_invalid_date(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "not-a-date,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid date", errors[0])

    def test_invalid_quantity(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,abc,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid quantity", errors[0])

    def test_invalid_price(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,abc,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid unit_price", errors[0])

    def test_missing_item_name(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("item_name is required", errors[0])

    def test_empty_csv(self):
        csv_content = ""
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("empty", errors[0].lower())

    def test_mixed_valid_and_invalid_rows(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
            "bad-date,Widget B,5,12.00,60.00,4.00,EC1A 1BB\n"
            "2024-03-10,Widget C,3,8.00,24.00,2.00,W1A 1AB\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 2)
        self.assertEqual(len(errors), 1)

    def test_whitespace_handling(self):
        csv_content = (
            "  date , item_name , quantity , unit_price , total_price , shipping_cost , post_code \n"
            " 2024-01-15 , Widget A , 10 , 5.00 , 50.00 , 3.50 , SW1A 1AA \n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["item_name"], "Widget A")
