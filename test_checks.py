import pandas as pd

from core.services.quality.checks import QualityChecks


dataframe = pd.read_csv("data/customers.csv")


checks = [
    QualityChecks.not_null(dataframe, "email"),
    QualityChecks.unique(dataframe, "customer_id"),
    QualityChecks.valid_email(dataframe, "email"),
    QualityChecks.range_check(
        dataframe,
        "age",
        minimum=0,
        maximum=120,
    ),
    QualityChecks.duplicate_rows(dataframe),
]


for result in checks:
    print("=" * 60)
    print(f"Check: {result.check_name}")
    print(f"Passed: {result.passed}")
    print(f"Rows checked: {result.rows_checked}")
    print(f"Rows passed: {result.rows_passed}")
    print(f"Rows failed: {result.rows_failed}")
    print(f"Details: {result.details}")