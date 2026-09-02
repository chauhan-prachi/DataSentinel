from core.services.ingestion.url_loader import URLLoader
from core.services.schema.detector import SchemaDetector
from core.services.quality.rule_suggester import RuleSuggester


url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"

loader = URLLoader()
detector = SchemaDetector()
suggester = RuleSuggester()

dataframe = loader.read(url)

schema_results = detector.detect(dataframe)

suggestions = suggester.suggest(schema_results)

print("=" * 70)
print("AUTOMATIC QUALITY RULE SUGGESTIONS")
print("=" * 70)

for suggestion in suggestions:
    print(
        f"{suggestion['column']:<20} "
        f"{suggestion['rule']:<20} "
        f"confidence={suggestion['confidence']:.2f}"
    )

    print(
        f"  Reason: {suggestion['reason']}"
    )