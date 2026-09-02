from pprint import pprint

from core.services.quality.engine import QualityEngine


engine = QualityEngine()

check_config = [
    {
        "check": "NOT_NULL",
        "column": "email",
    },
    {
        "check": "UNIQUE",
        "column": "customer_id",
    },
    {
        "check": "VALID_EMAIL",
        "column": "email",
    },
    {
        "check": "RANGE",
        "column": "age",
        "minimum": 0,
        "maximum": 120,
    },
    {
        "check": "DUPLICATE",
    },
]

result = engine.run_csv_checks(
    "data/customers.csv",
    check_config,
)

pprint(result["summary"])

for check in result["checks"]:
    print(
        check["check_name"],
        "→",
        "PASS" if check["passed"] else "FAIL",
    )