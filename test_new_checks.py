import pandas as pd

from core.services.quality.checks import QualityChecks


dataframe = pd.DataFrame(
    {
        "amount": [
            "100",
            "250.50",
            "invalid",
            "500",
            None,
        ],
        "date": [
            "2026-01-10",
            "2026-02-15",
            "invalid-date",
            "2026-04-20",
            None,
        ],
    }
)


numeric_result = QualityChecks.numeric_validity(
    dataframe,
    "amount",
)

date_result = QualityChecks.valid_date(
    dataframe,
    "date",
)


print("=" * 60)
print("NUMERIC VALIDITY")
print("=" * 60)
print(numeric_result)


print()
print("=" * 60)
print("VALID DATE")
print("=" * 60)
print(date_result)