from pprint import pprint

from core.services.ingestion.url_loader import URLLoader
from core.services.quality.engine import QualityEngine


URL = (
    "https://raw.githubusercontent.com/"
    "mwaskom/seaborn-data/master/iris.csv"
)


loader = URLLoader()
engine = QualityEngine()

print("=" * 70)
print("DATASENTINEL AUTOMATIC QUALITY ANALYSIS")
print("=" * 70)

dataframe = loader.read(URL)

print(f"Dataset: {URL}")
print(f"Rows: {len(dataframe)}")
print(f"Columns: {len(dataframe.columns)}")

print()
print("Running automatic analysis...")

result = engine.run_dataframe_checks(
    dataframe=dataframe,
    dataset_name=URL,
)

print()
print("=" * 70)
print("SCHEMA")
print("=" * 70)

for column in result["schema"]:
    print(
        f"{column['column']:<20}"
        f"{column['detected_type']:<18}"
        f"confidence={column['confidence']:.2f}"
    )

print()
print("=" * 70)
print("AUTOMATIC RULES")
print("=" * 70)

for suggestion in result["suggestions"]:
    print(
        f"{suggestion['column']:<20}"
        f"{suggestion['rule']:<20}"
        f"confidence={suggestion['confidence']:.2f}"
    )

print()
print("=" * 70)
print("QUALITY RESULTS")
print("=" * 70)

for check in result["checks"]:
    status = "PASS" if check["passed"] else "FAIL"

    print(
        f"{check['check_name']:<20}"
        f"{status:<8}"
        f"rows_failed={check['rows_failed']}"
    )

print()
print("=" * 70)
print("QUALITY SUMMARY")
print("=" * 70)

pprint(result["summary"])