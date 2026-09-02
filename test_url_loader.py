from core.services.ingestion.url_loader import URLLoader


url = "https://raw.githubusercontent.com/mwaskom/seaborn-data/master/iris.csv"

loader = URLLoader()

dataframe = loader.read(url)

print("Dataset loaded successfully.")
print(f"Rows: {len(dataframe)}")
print(f"Columns: {len(dataframe.columns)}")
print()
print("Columns:")
print(list(dataframe.columns))
print()
print("First 5 rows:")
print(dataframe.head())