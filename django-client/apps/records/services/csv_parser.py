import csv
import io
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any


class CSVParser(ABC):
    @abstractmethod
    def parse(self, file_content: str) -> tuple[list[dict[str, Any]], list[str]]:
        pass


class DefaultCSVParser(CSVParser):
    REQUIRED_FIELDS = [
        "date",
        "item_name",
        "quantity",
        "unit_price",
        "total_price",
        "shipping_cost",
        "post_code",
    ]
    OPTIONAL_FIELDS = ["currency"]
    DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"]

    def parse(self, file_content: str) -> tuple[list[dict[str, Any]], list[str]]:
        records = []
        errors = []

        reader = csv.DictReader(io.StringIO(file_content))

        if reader.fieldnames is None:
            errors.append("CSV file is empty or has no header row.")
            return records, errors

        normalised_fieldnames = [f.strip().lower() for f in reader.fieldnames]
        missing = [
            f for f in self.REQUIRED_FIELDS if f not in normalised_fieldnames
        ]
        if missing:
            errors.append(f"Missing required columns: {', '.join(missing)}")
            return records, errors

        for row_num, row in enumerate(reader, start=2):
            normalised_row = {k.strip().lower(): v.strip() for k, v in row.items()}
            row_errors = []
            parsed = {}

            parsed_date = self._parse_date(normalised_row.get("date", ""))
            if parsed_date is None:
                row_errors.append("invalid date format")
            else:
                parsed["date"] = parsed_date

            item_name = normalised_row.get("item_name", "").strip()
            if not item_name:
                row_errors.append("item_name is required")
            else:
                parsed["item_name"] = item_name

            for field in ("quantity",):
                val = normalised_row.get(field, "").strip()
                try:
                    parsed[field] = int(val)
                    if parsed[field] < 0:
                        row_errors.append(f"{field} must be non-negative")
                except (ValueError, TypeError):
                    row_errors.append(f"invalid {field}")

            for field in ("unit_price", "total_price", "shipping_cost"):
                val = normalised_row.get(field, "").strip()
                try:
                    parsed[field] = Decimal(val)
                except (InvalidOperation, TypeError):
                    row_errors.append(f"invalid {field}")

            post_code = normalised_row.get("post_code", "").strip()
            if not post_code:
                row_errors.append("post_code is required")
            else:
                parsed["post_code"] = post_code

            currency = normalised_row.get("currency", "").strip()
            parsed["currency"] = currency if currency else "GBP"

            if row_errors:
                errors.append(f"Row {row_num}: {'; '.join(row_errors)}")
            else:
                records.append(parsed)

        return records, errors

    def _parse_date(self, value: str) -> datetime | None:
        value = value.strip()
        if not value:
            return None
        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
        return None
