from core.services.ingestion.url_loader import URLLoader
from core.services.schema.detector import SchemaDetector


url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"

loader = URLLoader()
detector = SchemaDetector()

dataframe = loader.read(url)

results = detector.detect(dataframe)

print("=" * 70)
print("SCHEMA DETECTION")
print("=" * 70)

for result in results:
    print(
        f"{result['column']:<20} "
        f"{result['detected_type']:<15} "
        f"confidence={result['confidence']:.2f}"
    )

    print(
        f"  Reason: {result['reason']}"
    )