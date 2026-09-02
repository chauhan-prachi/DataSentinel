from __future__ import annotations

from dataclasses import asdict

import pandas as pd

from core.services.ingestion.url_loader import URLLoader
from core.services.schema.detector import SchemaDetector
from core.services.quality.rule_suggester import RuleSuggester
from core.services.quality.engine import QualityEngine


class AutomaticQualityAnalyzer:
    """
    Complete automatic data-quality analysis pipeline.

    URL
        ↓
    Load dataset
        ↓
    Profile dataset
        ↓
    Detect schema
        ↓
    Suggest quality rules
        ↓
    Execute rules
        ↓
    Calculate quality score
    """

    def __init__(self):
        self.loader = URLLoader()
        self.schema_detector = SchemaDetector()
        self.rule_suggester = RuleSuggester()
        self.engine = QualityEngine()

    def analyze_url(self, url: str) -> dict:
        # 1. Load dataset
        dataframe = self.loader.read(url)

        # 2. Profile dataset
        profile = self.engine.profiler.profile_dataframe(
            dataframe
        )

        # 3. Detect schema
        schema = self.schema_detector.detect(dataframe)

        # 4. Suggest quality rules
        rules = self.rule_suggester.suggest(schema)

        # 5. Convert suggestions into engine configuration
        check_config = self._build_check_config(rules)

        # 6. Execute checks
        results = self._run_checks(
            dataframe=dataframe,
            check_config=check_config,
        )

        # 7. Build summary
        summary = self._build_summary(results)

        return {
            "dataset": {
                "url": url,
                "rows": int(len(dataframe)),
                "columns": int(len(dataframe.columns)),
            },
            "profile": profile,
            "schema": schema,
            "rules": rules,
            "results": results,
            "summary": summary,
        }

    @staticmethod
    def _build_check_config(
        rules: list[dict],
    ) -> list[dict]:
        """
        Convert RuleSuggester output into
        QualityEngine-compatible configuration.
        """

        return [
            {
                "check": rule["rule"],
                "column": rule["column"],
            }
            for rule in rules
        ]

    def _run_checks(
        self,
        dataframe: pd.DataFrame,
        check_config: list[dict],
    ) -> list[dict]:
        """Execute all automatically suggested checks."""

        results = []

        for config in check_config:
            result = self.engine._run_check(
                dataframe=dataframe,
                check_type=config["check"],
                column=config.get("column"),
                config=config,
            )

            results.append(asdict(result))

        return results

    @staticmethod
    def _build_summary(
        results: list[dict],
    ) -> dict:
        """Build overall quality summary."""

        total_checks = len(results)

        passed_checks = sum(
            1
            for result in results
            if result["passed"]
        )

        failed_checks = total_checks - passed_checks

        quality_score = (
            round(
                passed_checks / total_checks * 100,
                2,
            )
            if total_checks
            else 0
        )

        return {
            "total_checks": total_checks,
            "passed_checks": passed_checks,
            "failed_checks": failed_checks,
            "quality_score": quality_score,
        }