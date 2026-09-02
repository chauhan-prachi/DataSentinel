import pandas as pd
from pprint import pprint

from core.services.schema.detector import SchemaDetector
from core.services.quality.rule_suggester import RuleSuggester
from core.services.quality.engine import QualityEngine


dataframe = pd.DataFrame(
    {
        "customer_id": [
            1001,
            1002,
            1003,
            1004,
            1005,
        ],
        "name": [
            "Aarav",
            "Priya",
            "Rahul",
            "Ananya",
            "Vikram",
        ],
        "email": [
            "aarav@example.com",
            "priya@example.com",
            "invalid-email",
            "ananya@example.com",
            None,
        ],
        "age": [
            25,
            31,
            28,
            None,
            42,
        ],
        "signup_date": [
            "2026-01-10",
            "2026-02-15",
            "invalid-date",
            "2026-04-20",
            "2026-05-12",
        ],
        "country": [
            "India",
            "India",
            "Germany",
            "India",
            "Germany",
        ],
        "is_active": [
            True,
            True,
            False,
            True,
            False,
        ],
    }
)


detector = SchemaDetector()
suggester = RuleSuggester()
engine = QualityEngine()


print("=" * 70)
print("REALISTIC DATASET TEST")
print("=" * 70)

print(f"Rows: {len(dataframe)}")
print(f"Columns: {len(dataframe.columns)}")

print()
print("=" * 70)
print("SCHEMA DETECTION")
print("=" * 70)

schema = detector.detect(dataframe)

for item in schema:
    print(
        f"{item['column']:<20}"
        f"{item['detected_type']:<18}"
        f"confidence={item['confidence']:.2f}"
    )

print()
print("=" * 70)
print("RULE SUGGESTIONS")
print("=" * 70)

suggestions = suggester.suggest(schema)

for item in suggestions:
    print(
        f"{item['column']:<20}"
        f"{item['rule']:<20}"
        f"confidence={item['confidence']:.2f}"
    )

print()
print("=" * 70)
print("QUALITY ANALYSIS")
print("=" * 70)

result = engine.run_dataframe_checks(
    dataframe=dataframe,
    dataset_name="realistic_customer_dataset",
)

for check in result["checks"]:
    status = "PASS" if check["passed"] else "FAIL"

    print(
        f"{check['check_name']:<20}"
        f"{status:<8}"
        f"rows_failed={check['rows_failed']}"
    )

print()
print("=" * 70)
print("SUMMARY")
print("=" * 70)

pprint(result["summary"])