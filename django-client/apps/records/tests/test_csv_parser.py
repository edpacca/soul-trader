from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import TestCase

from apps.records.services.csv_parser import DefaultCSVParser, POSTCODE_RE


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

    def test_postcode_extracted_from_full_address(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,123 Fake Street SW1A 1AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["post_code"], "SW1A 1AA")

    def test_postcode_plain_value_kept_when_no_match(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,12345\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["post_code"], "12345")

    def test_postcode_gir_special_case(self):
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,GIR 0AA\n"
        )
        records, errors = self.parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["post_code"], "GIR 0AA")


class TestPostcodeRegex(TestCase):
    def test_matches_standard_postcode(self):
        self.assertIsNotNone(POSTCODE_RE.search("SW1A 1AA"))

    def test_matches_postcode_in_address(self):
        match = POSTCODE_RE.search("10 Downing Street SW1A 2AA")
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0).strip(), "SW1A 2AA")

    def test_matches_gir(self):
        self.assertIsNotNone(POSTCODE_RE.search("GIR 0AA"))

    def test_no_match_for_non_postcode(self):
        self.assertIsNone(POSTCODE_RE.search("12345"))


def _make_profile(
    delimiter=",",
    date_format="%Y-%m-%d",
    field_mappings=None,
):
    profile = MagicMock()
    profile.delimiter = delimiter
    profile.date_format = date_format
    profile.field_mappings = field_mappings or {
        "0": "date",
        "1": "item_name",
        "2": "quantity",
        "3": "unit_price",
        "4": "total_price",
        "5": "shipping_cost",
        "6": "post_code",
    }
    return profile


class TestDefaultCSVParserWithProfile(TestCase):
    def test_parse_with_profile_valid_csv(self):
        profile = _make_profile()
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(records[0]["date"], date(2024, 1, 15))
        self.assertEqual(records[0]["item_name"], "Widget A")
        self.assertEqual(records[0]["quantity"], 10)
        self.assertEqual(records[0]["unit_price"], Decimal("5.00"))
        self.assertEqual(records[0]["post_code"], "SW1A 1AA")
        self.assertEqual(records[0]["currency"], "GBP")

    def test_parse_with_profile_custom_delimiter(self):
        profile = _make_profile(delimiter=";")
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date;item_name;quantity;unit_price;total_price;shipping_cost;post_code\n"
            "2024-01-15;Widget A;10;5.00;50.00;3.50;SW1A 1AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(len(errors), 0)
        self.assertEqual(records[0]["item_name"], "Widget A")

    def test_parse_with_profile_custom_date_format(self):
        profile = _make_profile(date_format="%d/%m/%Y")
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "15/01/2024,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["date"], date(2024, 1, 15))

    def test_parse_with_profile_wrong_date_format_errors(self):
        profile = _make_profile(date_format="%d/%m/%Y")
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("invalid date", errors[0])

    def test_parse_with_profile_reordered_columns(self):
        profile = _make_profile(
            field_mappings={
                "0": "item_name",
                "1": "date",
                "2": "quantity",
                "3": "unit_price",
                "4": "total_price",
                "5": "shipping_cost",
                "6": "post_code",
            }
        )
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "item_name,date,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "Widget A,2024-01-15,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["item_name"], "Widget A")
        self.assertEqual(records[0]["date"], date(2024, 1, 15))

    def test_parse_with_profile_missing_required_mapping(self):
        profile = _make_profile(
            field_mappings={
                "0": "date",
                "1": "item_name",
            }
        )
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name\n"
            "2024-01-15,Widget A\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("Missing required field mappings", errors[0])

    def test_parse_with_profile_column_out_of_range(self):
        profile = _make_profile(
            field_mappings={
                "0": "date",
                "1": "item_name",
                "2": "quantity",
                "3": "unit_price",
                "4": "total_price",
                "5": "shipping_cost",
                "99": "post_code",
            }
        )
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 0)
        self.assertIn("out of range", errors[0])

    def test_parse_with_profile_empty_csv(self):
        profile = _make_profile()
        parser = DefaultCSVParser(profile=profile)
        records, errors = parser.parse("")

        self.assertEqual(len(records), 0)
        self.assertEqual(len(errors), 1)
        self.assertIn("empty", errors[0].lower())

    def test_parse_with_profile_tab_delimiter(self):
        profile = _make_profile(delimiter="\\t")
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date\titem_name\tquantity\tunit_price\ttotal_price\tshipping_cost\tpost_code\n"
            "2024-01-15\tWidget A\t10\t5.00\t50.00\t3.50\tSW1A 1AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(len(errors), 0)

    def test_parse_with_profile_postcode_from_address(self):
        profile = _make_profile()
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,10 Downing Street SW1A 2AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["post_code"], "SW1A 2AA")

    def test_parse_with_profile_currency_mapping(self):
        profile = _make_profile(
            field_mappings={
                "0": "date",
                "1": "item_name",
                "2": "quantity",
                "3": "unit_price",
                "4": "total_price",
                "5": "shipping_cost",
                "6": "post_code",
                "7": "currency",
            }
        )
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code,currency\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA,USD\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["currency"], "USD")

    def test_parse_with_profile_default_currency_when_not_mapped(self):
        profile = _make_profile()
        parser = DefaultCSVParser(profile=profile)
        csv_content = (
            "date,item_name,quantity,unit_price,total_price,shipping_cost,post_code\n"
            "2024-01-15,Widget A,10,5.00,50.00,3.50,SW1A 1AA\n"
        )
        records, errors = parser.parse(csv_content)

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["currency"], "GBP")
