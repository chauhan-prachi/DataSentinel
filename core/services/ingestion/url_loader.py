from io import BytesIO
from urllib.parse import urlparse

import pandas as pd
import requests

from .base import DataSourceReader


class URLLoader(DataSourceReader):
    """Download and read supported datasets from HTTP/HTTPS URLs."""

    MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    TIMEOUT = (10, 60)

    def read(self, source: str) -> pd.DataFrame:
        self._validate_url(source)

        response = requests.get(
            source,
            stream=True,
            timeout=self.TIMEOUT,
            headers={
                "User-Agent": "DataSentinel/1.0"
            },
        )

        response.raise_for_status()

        content_length = response.headers.get(
            "Content-Length"
        )

        if content_length:
            if int(content_length) > self.MAX_DOWNLOAD_SIZE:
                raise ValueError(
                    "Remote dataset exceeds the 50 MB download limit."
                )

        content = bytearray()

        for chunk in response.iter_content(
            chunk_size=1024 * 1024
        ):
            if not chunk:
                continue

            content.extend(chunk)

            if len(content) > self.MAX_DOWNLOAD_SIZE:
                raise ValueError(
                    "Remote dataset exceeds the 50 MB download limit."
                )

        return self._parse_csv(
            bytes(content),
            source,
        )

    @staticmethod
    def _validate_url(source: str) -> None:
        parsed = urlparse(source)

        if parsed.scheme not in {"http", "https"}:
            raise ValueError(
                "Only HTTP and HTTPS URLs are supported."
            )

        if not parsed.netloc:
            raise ValueError(
                "Invalid dataset URL."
            )

    @staticmethod
    def _parse_csv(
        content: bytes,
        source: str,
    ) -> pd.DataFrame:
        try:
            return pd.read_csv(BytesIO(content))
        except Exception as exc:
            raise ValueError(
                f"Unable to parse remote CSV dataset: {source}"
            ) from exc