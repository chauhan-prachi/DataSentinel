from core.services.ingestion.url_loader import URLLoader
from core.services.quality.profiler import DatasetProfiler


url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"

loader = URLLoader()
profiler = DatasetProfiler()

dataframe = loader.read(url)

profile = profiler.profile_dataframe(dataframe)

print("=" * 60)
print("DATASET PROFILE")
print("=" * 60)

print(f"Rows: {profile['row_count']}")
print(f"Columns: {profile['column_count']}")

print()

for column in profile["columns"]:
    print(
        f"{column['name']}: "
        f"dtype={column['dtype']}, "
        f"nulls={column['null_count']}, "
        f"unique={column['unique_count']}, "
        f"duplicates={column['duplicate_count']}"
    )