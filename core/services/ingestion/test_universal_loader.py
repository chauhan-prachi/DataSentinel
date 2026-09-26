from pathlib import Path
from tempfile import TemporaryDirectory
from xml.etree.ElementTree import Element, SubElement, ElementTree
import pandas as pd
from core.services.ingestion.universal_loader import UniversalLoader

BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = BASE_DIR / "media" / "datasets"


def test_existing_csv_files():
    loader = UniversalLoader()

    test_files = list(DATA_DIR.glob("*.csv"))

    if not test_files:
        raise FileNotFoundError(
            f"No CSV datasets found in: {DATA_DIR}"
        )

    for file_path in test_files:
        dataframe = loader.read(file_path)

        print(f"\n{file_path.name}")
        print(f"Rows: {len(dataframe)}")
        print(f"Columns: {len(dataframe.columns)}")
        print(f"Column names: {list(dataframe.columns)}")

        assert isinstance(dataframe, pd.DataFrame)
        assert not dataframe.empty


def create_xml_file(dataframe: pd.DataFrame, file_path: Path) -> None:
    root = Element("dataset")

    for _, row in dataframe.iterrows():
        record = SubElement(root, "record")

        for column in dataframe.columns:
            element = SubElement(record, str(column))
            value = row[column]
            element.text = "" if pd.isna(value) else str(value)

    tree = ElementTree(root)
    tree.write(file_path, encoding="utf-8", xml_declaration=True)


def create_test_files(directory: Path) -> dict[str, Path]:
    dataframe = pd.DataFrame(
        {
            "name": ["Prachi", "Aman", "Riya"],
            "age": [23, 25, 22],
            "email": [
                "prachi@example.com",
                "aman@example.com",
                "riya@example.com",
            ],
        }
    )

    files = {}

    csv_path = directory / "sample.csv"
    dataframe.to_csv(csv_path, index=False)
    files["CSV"] = csv_path

    json_path = directory / "sample.json"
    dataframe.to_json(json_path, orient="records", indent=4)
    files["JSON"] = json_path

    excel_path = directory / "sample.xlsx"
    dataframe.to_excel(excel_path, index=False, engine="openpyxl")
    files["EXCEL"] = excel_path

    parquet_path = directory / "sample.parquet"
    dataframe.to_parquet(parquet_path, index=False)
    files["PARQUET"] = parquet_path

    tsv_path = directory / "sample.tsv"
    dataframe.to_csv(tsv_path, sep="\t", index=False)
    files["TSV"] = tsv_path

    xml_path = directory / "sample.xml"
    create_xml_file(dataframe, xml_path)
    files["XML"] = xml_path

    return files


def test_multiple_formats():
    loader = UniversalLoader()

    expected_columns = ["name", "age", "email"]
    expected_rows = 3

    with TemporaryDirectory() as temp_directory:
        directory = Path(temp_directory)
        test_files = create_test_files(directory)

        for expected_format, file_path in test_files.items():
            dataframe = loader.read(file_path)

            assert isinstance(dataframe, pd.DataFrame)
            assert not dataframe.empty
            assert len(dataframe) == expected_rows
            assert list(dataframe.columns) == expected_columns

            print(
                f"{expected_format:8} -> PASS | "
                f"{len(dataframe)} rows x "
                f"{len(dataframe.columns)} columns"
            )


def test_loader():
    test_existing_csv_files()
    test_multiple_formats()

    print()
    print("All UniversalLoader tests passed successfully.")


if __name__ == "__main__":
    test_loader()
