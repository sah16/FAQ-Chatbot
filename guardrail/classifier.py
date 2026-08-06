"""Intent classification layer implementing the pre-retrieval refusal guardrail.
Ensures advisory, comparative, performance prediction, out-of-scope, and prompt injection queries
are blocked and refused before reaching retrieval or generation.
"""

import re
from typing import Tuple, Optional
from guardrail.taxonomy import TaxonomyManager, IntentCategory, RefusalResponse


class IntentClassifier:
    """Pre-retrieval intent classifier for compliance and refusal handling."""

    def __init__(self, taxonomy_manager: Optional[TaxonomyManager] = None):
        self.taxonomy = taxonomy_manager or TaxonomyManager()

        # Prompt injection & jailbreak patterns
        self.prompt_injection_patterns = [
            r"\b(ignore (all|your|previous|any) (instructions|rules|constraints))\b",
            r"\b(bypass (rules|guardrails|safety|restrictions|filters))\b",
            r"\b(act as (a|an|my)?\s*(financial advisor|portfolio manager|investment planner|unrestricted|expert))\b",
            r"\b(jailbreak|system prompt|developer mode|dan mode)\b",
            r"\b(disregard constraints|pretend you (are|can))\b",
            r"\b(forget (your|the) (rules|instructions))\b"
        ]

        # Advisory patterns (explicit investment recommendation / opinion seeking)
        self.advisory_patterns = [
            r"\b(should i (invest|buy|sell|redeem|hold|choose|pick|start|stop|put money|exit))\b",
            r"\b(is it (a\s+)?(good|safe|worth|profitable|wise|better|right)\s*(time\s*)?to (invest|buy|sell|redeem|put money|enter|exit))\b",
            r"\b((a\s+)?(good|right|best)\s+time to (buy|invest|sell|redeem|enter|exit))\b",
            r"\b(recommend|suggest|give advice|advise me|best fund to invest)\b",
            r"\b(portfolio advice|investment advice|financial advice)\b",
            r"\b(where should i invest|how should i invest|how much should i invest|how much should i put)\b",
            r"\b(when to exit|when to sell|when to redeem|should i exit|should i redeem)\b",
            r"\b(is this fund (a\s+)?good (for|option|choice))\b",
            r"\b(give me (a recommendation|stock tip|mutual fund tip))\b"
        ]

        # Comparative patterns
        self.comparative_patterns = [
            r"\b(which (fund|scheme|one) is (better|best|superior|safer|more profitable|preferred))\b",
            r"\b(compare|comparison between|comparison of)\b",
            r"\b\b(vs|versus)\b",
            r"\b(is .+ better than .+)\b",
            r"\b(difference between .+ and .+)\b"
        ]

        # Performance prediction patterns
        self.performance_patterns = [
            r"\b(what returns will i get|how much return|calculate returns|future returns?|expected returns?)\b",
            r"\b(predict|forecast|cagr in \d+ years?|estimate future value)\b",
            r"\b(will this fund grow|will i get \d+%\s*returns?)\b",
            r"\b(how much money will i make|calculate profit|how much profit)\b"
        ]

        # Out-of-corpus patterns (non-HDFC schemes, non-mutual-fund assets, unrelated services)
        self.out_of_corpus_patterns = [
            r"\b(sbi|icici|axis|nippon|quant|mirae|tata|kotak|uti|parag parikh|dsp|motilal|canara|franklin|bandhan|aditya birla|edelweiss|invesco|pgim)\b",
            r"\b(crypto|bitcoin|ethereum|btc|eth|gold loan|fixed deposit|fd interest|real estate|stock tips|intraday|option trading|futures and options|f&o)\b",
            r"\b(itr|tax filing|itr-1|itr-2|gst portal|itr filing|income tax refund)\b"
        ]

    def classify(self, query: str) -> IntentCategory:
        """Classifies the query intent category."""
        q_clean = query.strip().lower()

        # 1. Check prompt injection / jailbreak attempts first
        for pat in self.prompt_injection_patterns:
            if re.search(pat, q_clean):
                return IntentCategory.ADVISORY

        # 2. Check for out-of-corpus non-HDFC schemes / external domains
        for pat in self.out_of_corpus_patterns:
            if re.search(pat, q_clean):
                return IntentCategory.OUT_OF_CORPUS

        # 3. Check for comparative queries
        for pat in self.comparative_patterns:
            if re.search(pat, q_clean):
                return IntentCategory.COMPARATIVE

        # 4. Check for advisory queries
        is_advisory = any(re.search(pat, q_clean) for pat in self.advisory_patterns)
        
        # 5. Check for performance prediction queries
        is_perf = any(re.search(pat, q_clean) for pat in self.performance_patterns)

        # 6. Check if there is also an in-corpus factual anchor (using word boundaries)
        factual_anchor_pattern = re.compile(
            r"\b(expense ratio|ter|exit load|minimum sip|min sip|minimum lumpsum|lumpsum|riskometer|benchmark|lock-in|lock in|fund manager|account statement|capital gains)\b"
        )
        has_factual_anchor = bool(factual_anchor_pattern.search(q_clean))

        if is_advisory and has_factual_anchor:
            return IntentCategory.MIXED_INTENT

        if is_advisory:
            return IntentCategory.ADVISORY

        if is_perf:
            return IntentCategory.PERFORMANCE_PREDICTION

        return IntentCategory.FACTUAL_IN_CORPUS

    def evaluate(self, query: str) -> Tuple[IntentCategory, RefusalResponse]:
        """Classifies query and returns refusal response if refusal is triggered."""
        category = self.classify(query)
        refusal = self.taxonomy.create_refusal(category)
        return category, refusal
