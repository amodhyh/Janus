"""
Janus Security Engine - Pass 1: Deterministic & Regex Inspection Stage
Implements the PipelineStage protocol for fast-path PII redaction, secret protection,
and sub-millisecond jailbreak short-circuiting.
"""

import re
from typing import Dict, List, Pattern, Optional

try:
    from .pipelineDTO import PipelineDTO, DTODecision
except (ImportError, ModuleNotFoundError):
    try:
        from pipeline.pipelineDTO import PipelineDTO, DTODecision
    except (ImportError, ModuleNotFoundError):
        from pipelineDTO import PipelineDTO, DTODecision


# ==============================================================================
# PERSONALLY IDENTIFIABLE INFORMATION (PII) PATTERNS
# ==============================================================================

# RFC 5322 Pragmatic Email Pattern
# Word boundaries (\b) allow detection inside conversational prompts.
EMAIL_PATTERN: Pattern[str] = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE
)

# Major Credit Card Networks (Visa, MasterCard, Amex, Discover)
# Captures both contiguous 13-16 digit numbers AND common delimiter formats (dashes, spaces).
CREDIT_CARD_PATTERN: Pattern[str] = re.compile(
    r"\b(?:"
    # Visa: 13 or 16 digits starting with 4
    r"4[0-9]{3}(?:[- ]?[0-9]{4}){3}"
    r"|4[0-9]{12}"
    # MasterCard: 51-55 or 2221-2720
    r"|5[1-5][0-9]{2}(?:[- ]?[0-9]{4}){3}"
    r"|2(?:2[2-9][0-9]|2[3-9][0-9]{2}|[3-6][0-9]{3}|7[0-1][0-9]{2}|720[0-9])(?:[- ]?[0-9]{4}){2}[- ]?[0-9]{4}"
    # American Express: 15 digits starting with 34 or 37 (4-6-5 grouping)
    r"|3[47][0-9]{2}[- ]?[0-9]{6}[- ]?[0-9]{5}"
    # Discover: 6011, 65, 644-649
    r"|6(?:011|5[0-9]{2})(?:[- ]?[0-9]{4}){3}"
    r")\b"
)

# US Social Security Number (SSN)
# Enforces valid Area (AAA != 000, 666, 900-999), Group (GG != 00), and Serial (SSSS != 0000) ranges.
SSN_PATTERN: Pattern[str] = re.compile(
    r"\b(?!000|666|9\d{2})([0-9]{3})[- ]?(?!00)([0-9]{2})[- ]?(?!0000)([0-9]{4})\b"
)


# ==============================================================================
# 2. CREDENTIAL & SECRET LEAKAGE PATTERNS
# ==============================================================================

SECRET_PATTERNS: Dict[str, Pattern[str]] = {
    # OpenAI Legacy (sk-...) and Project-Scoped (sk-proj-...) API Keys
    "OPENAI_API_KEY": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b"),
    
    # GitHub Personal Access Tokens (ghp, gho, ghu, ghs, ghr)
    "GITHUB_TOKEN": re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b"),
    
    # AWS Access Key ID (standard 20-character identifier starting with AKIA or ASIA)
    "AWS_ACCESS_KEY": re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),
    
    # Generic Private Key Header
    "PRIVATE_KEY_HEADER": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}


# ==============================================================================
# 3. DETERMINISTIC JAILBREAK & INJECTION SIGNATURES
# ==============================================================================

JAILBREAK_PATTERNS: List[Pattern[str]] = [
    # System Instruction Overrides
    re.compile(
        r"\b(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|directives)\b",
        re.IGNORECASE
    ),
    # Persona / Mode Switching (DAN, Developer Mode, etc.)
    re.compile(
        r"\b(?:you\s+are\s+now|act\s+as)\s+(?:DAN|Jailbreak(?:ed)?|an?\s+unrestricted\s+AI|evil\s+bot)\b",
        re.IGNORECASE
    ),
    re.compile(
        r"\bdeveloper\s+mode\s+(?:is\s+)?enabled\b",
        re.IGNORECASE
    ),
    # System Prompt Leak / Extraction Attempts
    re.compile(
        r"\b(?:print|output|display|show|reveal)\s+(?:your\s+)?(?:system\s+prompt|initial\s+instructions)\b",
        re.IGNORECASE
    ),
]
#  LUHN ALGORITHM (MODULO 10 CHECKSUM)

def is_luhn_valid(candidate: str) -> bool:
    """
    Validates candidate credit card digits via the Luhn (Mod 10) algorithm.
    Operates in a single reverse pass without heap-allocating intermediate lists.
    
    Time Complexity: O(N) where N is number of digits (13 <= N <= 19).
    Space Complexity: O(1) auxiliary memory.
    """
    total_digits = 0
    checksum = 0
    is_second = False
    
    for char in reversed(candidate):
        if not char.isdigit():
            continue
        total_digits += 1
        digit = ord(char) - 48  # Fast ASCII to integer conversion
        
        if is_second:
            doubled = digit * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += digit
            
        is_second = not is_second
        
    if total_digits < 13 or total_digits > 19:
        return False
        
    return checksum % 10 == 0


class RegexStage:
    """
    Pass 1 Deterministic Inspection Stage.
    
    Satisfies the PipelineStage structural protocol:
        process(prompt: str) -> PipelineDTO
    """

    def process(self, prompt: str) -> PipelineDTO:
        
        # jailbreak Check (Short-circuit Denial)
        for pattern in JAILBREAK_PATTERNS:
            match = pattern.search(prompt)
            if match:
                
                return PipelineDTO(
                    action=DTODecision.DENY,
                    prompt=prompt,
                    is_final=True,
                    reason=f"Deterministic jailbreak signature matched: '{match.group(0)}'"
                )

        mutated_prompt = prompt
        mutations_count = 0

        # Secret & Credential Leakage Redaction
        for secret_name, pattern in SECRET_PATTERNS.items():
            mutated_prompt, count = pattern.subn(f"<REDACTED_{secret_name}>", mutated_prompt)
            mutations_count += count

        #  Credit Card Redaction with Luhn Verification
        def _redact_card_if_valid(match: re.Match) -> str:
            nonlocal mutations_count
            raw_token = match.group(0)
            if is_luhn_valid(raw_token):
                mutations_count += 1
                return "<REDACTED_CREDIT_CARD>"
            # If Luhn checksum fails, it's likely a serial/tracking number; leave intact.
            return raw_token

        mutated_prompt = CREDIT_CARD_PATTERN.sub(_redact_card_if_valid, mutated_prompt)

        #  Email & SSN Redaction
        mutated_prompt, email_count = EMAIL_PATTERN.subn("<REDACTED_EMAIL>", mutated_prompt)
        mutations_count += email_count

        mutated_prompt, ssn_count = SSN_PATTERN.subn("<REDACTED_SSN>", mutated_prompt)
        mutations_count += ssn_count

        #  Construct Final DTO for Subsequent Stages
        if mutations_count > 0:
            return PipelineDTO(
                action=DTODecision.MUTATE,
                prompt=mutated_prompt,
                is_final=False,
                reason=f"Pass 1 redacted {mutations_count} sensitive token(s)"
            )

        return PipelineDTO(
            action=DTODecision.ALLOW,
            prompt=prompt,
            is_final=False,
            reason="Pass 1 deterministic checks clean"
        )


# Global singleton instance for functional or direct invocation
_default_stage = RegexStage()

def regex_analyze(prompt: str) -> PipelineDTO:
    """
    Convenience function invoking the default RegexStage instance.
    Maintains compatibility with functional entry points.
    """
    return _default_stage.process(prompt)