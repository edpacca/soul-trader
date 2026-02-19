import csv
import io
import re
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from apps.records.models import CSVFormatProfile

POSTCODE_RE = re.compile(
    r"([Gg][Ii][Rr] 0[Aa]{2})"
    r"|"
    r"(([A-Za-z][0-9]{1,2})"
    r"|([A-Za-z][A-Ha-hJ-Yj-y][0-9]{1,2})"
    r"|([A-Za-z][0-9][A-Za-z])"
    r"|([A-Za-z][A-Ha-hJ-Yj-y][0-9]?[A-Za-z]))"
    r"\s*[0-9][A-Za-z]{2}"
)


class CSVParser(ABC):
    def __init__(self, profile: "CSVFormatProfile | None" = None) -> None:
        self.profile = profile

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
        if self.profile is not None:
            return self._parse_with_profile(file_content)
        return self._parse_legacy(file_content)

    def _parse_with_profile(self, file_content: str) -> tuple[list[dict[str, Any]], list[str]]:
        records: list[dict[str, Any]] = []
        errors: list[str] = []

        delimiter = self.profile.delimiter
        if delimiter == "\\t":
            delimiter = "\t"

        reader = csv.reader(io.StringIO(file_content), delimiter=delimiter)
        rows = list(reader)

        if not rows:
            errors.append("CSV file is empty or has no header row.")
            return records, errors

        csv_headers = rows[0]
        mappings = self.profile.field_mappings
        date_format = self.profile.date_format

        mapped_fields = set(mappings.values())
        required_model_fields = set(self.REQUIRED_FIELDS)
        missing_required = required_model_fields - mapped_fields
        if missing_required:
            errors.append(
                f"Missing required field mappings: {', '.join(sorted(missing_required))}"
            )
            return records, errors

        for col_index_str in mappings:
            col_index = int(col_index_str)
            if col_index >= len(csv_headers):
                errors.append(
                    f"Column index {col_index} is out of range "
                    f"(CSV has {len(csv_headers)} columns)."
                )
                return records, errors

        data_rows = rows[1:]
        for row_num, row in enumerate(data_rows, start=2):
            row_errors: list[str] = []
            parsed: dict[str, Any] = {}

            for col_index_str, field_name in mappings.items():
                col_index = int(col_index_str)
                if col_index >= len(row):
                    row_errors.append(f"Column {col_index} out of range")
                    continue
                raw_value = row[col_index].strip()

                if field_name == "date":
                    if not raw_value:
                        row_errors.append("invalid date format")
                    else:
                        try:
                            parsed["date"] = datetime.strptime(raw_value, date_format).date()
                        except ValueError:
                            row_errors.append("invalid date format")
                elif field_name == "item_name":
                    if not raw_value:
                        row_errors.append("item_name is required")
                    else:
                        parsed["item_name"] = raw_value
                elif field_name == "quantity":
                    try:
                        parsed["quantity"] = int(raw_value)
                        if parsed["quantity"] < 0:
                            row_errors.append("quantity must be non-negative")
                    except (ValueError, TypeError):
                        row_errors.append("invalid quantity")
                elif field_name in ("unit_price", "total_price", "shipping_cost"):
                    try:
                        parsed[field_name] = Decimal(raw_value)
                    except (InvalidOperation, TypeError):
                        row_errors.append(f"invalid {field_name}")
                elif field_name == "post_code":
                    if not raw_value:
                        row_errors.append("post_code is required")
                    else:
                        match = POSTCODE_RE.search(raw_value)
                        if match:
                            parsed["post_code"] = match.group(0).strip()
                        else:
                            parsed["post_code"] = raw_value
                elif field_name == "currency":
                    parsed["currency"] = raw_value if raw_value else "GBP"
                else:
                    parsed[field_name] = raw_value

            if "currency" not in parsed and "currency" not in mapped_fields:
                parsed["currency"] = "GBP"

            if row_errors:
                errors.append(f"Row {row_num}: {'; '.join(row_errors)}")
            else:
                records.append(parsed)

        return records, errors

    def _parse_legacy(self, file_content: str) -> tuple[list[dict[str, Any]], list[str]]:
        records: list[dict[str, Any]] = []
        errors: list[str] = []

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
            row_errors: list[str] = []
            parsed: dict[str, Any] = {}

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

            post_code_raw = normalised_row.get("post_code", "").strip()
            if not post_code_raw:
                row_errors.append("post_code is required")
            else:
                match = POSTCODE_RE.search(post_code_raw)
                if match:
                    parsed["post_code"] = match.group(0).strip()
                else:
                    parsed["post_code"] = post_code_raw

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
