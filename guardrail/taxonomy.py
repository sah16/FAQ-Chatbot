"""Taxonomy definitions and refusal message generator."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class IntentCategory(str, Enum):
    """Refusal and routing taxonomy categories."""
    FACTUAL_IN_CORPUS = "factual_in_corpus"
    ADVISORY = "advisory"
    COMPARATIVE = "comparative"
    PERFORMANCE_PREDICTION = "performance_prediction"
    OUT_OF_CORPUS = "out_of_corpus"
    MIXED_INTENT = "mixed_intent"


class RefusalResponse(BaseModel):
    """Structured refusal response adhering to compliance standards."""
    refused: bool
    category: IntentCategory
    message: str
    educational_url: Optional[str] = None
    disclaimer: str = "Facts-only. No investment advice."


class TaxonomyManager:
    """Loads and formats refusal messages from taxonomy config."""

    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            config_path = Path(__file__).resolve().parent.parent / "config" / "taxonomy.json"
        self.config_path = config_path
        self.data = self._load_taxonomy()

    def _load_taxonomy(self) -> Dict:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Taxonomy config not found at {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def disclaimer(self) -> str:
        return self.data.get("disclaimer", "Facts-only. No investment advice.")

    @property
    def educational_url(self) -> str:
        return self.data.get("educational_resource", {}).get(
            "url", "https://www.amfiindia.com/investor-corner/investor-education"
        )

    def get_category_config(self, category_id: str) -> Optional[Dict]:
        for cat in self.data.get("categories", []):
            if cat.get("id") == category_id:
                return cat
        return None

    def create_refusal(self, category: IntentCategory) -> RefusalResponse:
        """Constructs a compliant refusal response for a given intent category."""
        if category == IntentCategory.FACTUAL_IN_CORPUS:
            return RefusalResponse(
                refused=False,
                category=category,
                message="",
                educational_url=None,
                disclaimer=self.disclaimer
            )

        cat_cfg = self.get_category_config(category.value)
        if cat_cfg and "refusal_message" in cat_cfg:
            msg = cat_cfg["refusal_message"]
        else:
            template = self.data.get(
                "default_refusal_template",
                "I can only share verified facts from official sources — I'm not able to offer investment advice or compare funds. For general guidance on choosing mutual funds, see AMFI's investor education resources: {educational_url}"
            )
            msg = template.format(educational_url=self.educational_url)

        return RefusalResponse(
            refused=True,
            category=category,
            message=msg,
            educational_url=self.educational_url,
            disclaimer=self.disclaimer
        )
