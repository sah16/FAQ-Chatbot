"""Generation pipeline interface and prompt constraint manager.
Calls Groq Cloud LLM (openai/gpt-oss-20b) with strict context-grounded prompt contract,
handles mixed-intent splits, and passes generation through the deterministic post-processor.
"""

import os
import re
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

from generation.formatter import AnswerFormatter, FormattedResponse
from ingestion.models import VectorRecord
from ingestion.pipeline import IngestionPipeline


def _load_env_file() -> Dict[str, str]:
    """Loads key-value pairs from .env file if present."""
    env_vars: Dict[str, str] = {}
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars


class GenerationPipeline:
    """Handles constrained generation with LLM context grounding and deterministic formatting."""

    SYSTEM_PROMPT = (
        "You are a factual, objective Mutual Fund FAQ Assistant for 5 specific HDFC mutual fund schemes.\n"
        "You must strictly adhere to the following rules:\n"
        "1. State ONLY facts that are explicitly present in the provided context chunks.\n"
        "2. NEVER provide investment advice, opinions, recommendations (such as whether to buy, sell, invest, or redeem), fund comparisons, or return predictions.\n"
        "3. Always answer in 3 sentences or fewer.\n"
        "4. If the provided context chunks do not contain the answer, state that you do not have a verified source for it.\n"
        "5. If a question mixes a factual part and an advisory part, answer ONLY the factual part."
    )

    ADVISORY_REFUSAL_NOTE = (
        "\n\nNote: I cannot offer investment advice or recommendations on whether to buy, sell, or hold. "
        "For educational guidance, please visit AMFI: https://www.amfiindia.com/investor-corner/knowledge-center/what-are-mutual-funds.html"
    )

    def __init__(
        self,
        formatter: Optional[AnswerFormatter] = None,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None
    ):
        self.formatter = formatter or AnswerFormatter()
        self.ingestion = self.formatter.ingestion

        # Load configuration
        env_vars = _load_env_file()
        self.api_key = api_key or os.getenv("GROQ_API_KEY") or env_vars.get("GROQ_API_KEY")
        self.model_name = model_name or os.getenv("GROQ_MODEL") or env_vars.get("GROQ_MODEL", "openai/gpt-oss-20b")
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"

    def _call_groq_api(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Calls Groq Chat Completions API with low temperature and bounded tokens."""
        if not self.api_key:
            return None

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.0,
            "max_tokens": 300
        }

        try:
            resp = requests.post(self.api_url, headers=headers, json=payload, timeout=12)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"].get("content", "")
                if content:
                    return content.strip()
        except Exception:
            pass

        return None

    def _fallback_synthesis(self, query: str, top_chunk: Optional[VectorRecord]) -> str:
        """Deterministic local fallback if API is unreachable or context is provided directly."""
        if not top_chunk:
            return "I do not have a verified source for this information."
        
        # Clean section text and return concise fact
        clean_text = re.sub(r"\[.*?\]", "", top_chunk.text).strip()
        sentences = self.formatter.split_sentences(clean_text)
        return " ".join(sentences[:2]) if sentences else clean_text

    def generate(
        self,
        query: str,
        chunks: List[VectorRecord],
        detected_scheme: Optional[str] = None,
        is_mixed_intent: bool = False
    ) -> FormattedResponse:
        """
        Executes constrained generation pipeline:
        1. Assembles retrieved context chunks.
        2. Queries Groq Cloud LLM with system prompt contract.
        3. Falls back to deterministic synthesis if API unavailable.
        4. Handles mixed-intent advisory refusal note.
        5. Formats and validates response via AnswerFormatter.
        """
        top_chunk = chunks[0] if chunks else None

        # Resolve citation URL and date from top chunk metadata
        if top_chunk:
            citation_url = top_chunk.source_url
            fetched_at = top_chunk.fetched_at
            citation_title = top_chunk.scheme_name
        else:
            sources = self.ingestion.get_sources()
            target_source = sources[0]
            if detected_scheme:
                for s in sources:
                    if s.id == detected_scheme:
                        target_source = s
                        break
            citation_url = target_source.url
            fetched_at = "2026-08-06"
            citation_title = target_source.name

        # Build prompt context
        context_blocks = []
        for i, c in enumerate(chunks[:3], 1):
            context_blocks.append(f"[Chunk {i}] ({c.scheme_name} - {c.section_label}):\n{c.text}")
        context_str = "\n\n".join(context_blocks)

        user_prompt = (
            f"Context information:\n{context_str}\n\n"
            f"User Question: {query}\n\n"
            f"Provide a factual answer in 3 sentences or fewer based strictly on the context above. Do not include markdown links in your answer."
        )

        generated_raw = self._call_groq_api(user_prompt, self.SYSTEM_PROMPT)

        if not generated_raw:
            generated_raw = self._fallback_synthesis(query, top_chunk)

        # Enforce max 3 sentences on generated text before appending any mixed-intent note
        clean_generated, _ = self.formatter.truncate_to_max_sentences(generated_raw, max_sentences=3)

        # Format through AnswerFormatter (validates URL and appends source citation + date footer)
        formatted = self.formatter.format_response(
            raw_text=clean_generated,
            citation_url=citation_url,
            fetched_at=fetched_at,
            citation_title=citation_title,
            auto_truncate=True
        )

        # If mixed intent, attach advisory refusal note
        if is_mixed_intent:
            formatted.text = formatted.text + self.ADVISORY_REFUSAL_NOTE

        return formatted

    def generate_noop(self, query: str, detected_scheme: Optional[str] = None) -> FormattedResponse:
        """Fast fallback generation."""
        sources = self.ingestion.get_sources()
        target_source = sources[0]

        if detected_scheme:
            for s in sources:
                if s.id == detected_scheme:
                    target_source = s
                    break

        sample_fact = f"For {target_source.name}, verified scheme facts and disclosures are available on Groww."
        return self.formatter.format_response(
            raw_text=sample_fact,
            citation_url=target_source.url,
            fetched_at="2026-08-06",
            citation_title=target_source.name,
            auto_truncate=True
        )
