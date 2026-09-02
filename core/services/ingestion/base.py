from abc import ABC, abstractmethod

import pandas as pd


class DataSourceReader(ABC):
    """Base interface for all DataSentinel data readers."""

    @abstractmethod
    def read(self, source: str) -> pd.DataFrame:
        """Read a data source and return a pandas DataFrame."""
        raise NotImplementedError