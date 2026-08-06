"""Input sanitation and PII stripping layer.
Ensures PAN, Aadhaar, phone numbers, and emails are never logged, stored, or echoed.
"""

import re
from typing import Tuple, List, Dict

# Regex patterns for Indian financial context
PAN_PATTERN = re.compile(r"\b[A-Za-z]{5}[0-9]{4}[A-Za-z]\b")
AADHAAR_PATTERN = re.compile(r"\b\d{4}[ -]\d{4}[ -]\d{4}\b|\b\d{12}\b")
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"(?:\+91[\s\-]?)?[6789]\d{9}\b")
FOLIO_ACCOUNT_PATTERN = re.compile(
    r"\b(?:folio|account|a/c|demat|dp\s*id)[\s\:\#\-]*([0-9A-Za-z]{8,20})\b",
    re.IGNORECASE
)


def detect_pii(text: str) -> Dict[str, bool]:
    """Detects whether any PII pattern exists in the text."""
    return {
        "has_pan": bool(PAN_PATTERN.search(text)),
        "has_aadhaar": bool(AADHAAR_PATTERN.search(text)),
        "has_email": bool(EMAIL_PATTERN.search(text)),
        "has_phone": bool(PHONE_PATTERN.search(text)),
        "has_folio_or_account": bool(FOLIO_ACCOUNT_PATTERN.search(text)),
    }


def sanitize_query(query: str) -> Tuple[str, bool]:
    """
    Sanitizes user input by redacting any detected PII tokens.
    Returns (cleaned_query, pii_was_detected).
    """
    if not query:
        return "", False

    sanitized = query
    pii_found = False

    # PAN replacement
    if PAN_PATTERN.search(sanitized):
        sanitized = PAN_PATTERN.sub("[REDACTED_PAN]", sanitized)
        pii_found = True

    # Email replacement
    if EMAIL_PATTERN.search(sanitized):
        sanitized = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", sanitized)
        pii_found = True

    # Folio / Account replacement (specific context before generic numbers)
    if FOLIO_ACCOUNT_PATTERN.search(sanitized):
        def _replace_acc(m):
            val = m.group(1)
            return m.group(0).replace(val, "[REDACTED_ACCOUNT]")
        sanitized = FOLIO_ACCOUNT_PATTERN.sub(_replace_acc, sanitized)
        pii_found = True

    # Aadhaar replacement
    if AADHAAR_PATTERN.search(sanitized):
        sanitized = AADHAAR_PATTERN.sub("[REDACTED_AADHAAR]", sanitized)
        pii_found = True

    # Phone replacement
    if PHONE_PATTERN.search(sanitized):
        sanitized = PHONE_PATTERN.sub("[REDACTED_PHONE]", sanitized)
        pii_found = True

    # Normalize multiple whitespace
    sanitized = re.sub(r"\s+", " ", sanitized).strip()

    return sanitized, pii_found


class PiiScrubber:
    """Helper wrapper for PII sanitization and detection."""

    def sanitize(self, text: str) -> Tuple[str, bool]:
        return sanitize_query(text)

    def detect(self, text: str) -> Dict[str, bool]:
        return detect_pii(text)

