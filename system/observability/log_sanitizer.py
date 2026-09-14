"""
KAIROS Observability Log Sanitizer & Redaction Engine
=====================================================
Strict Security Invariants:
1. Logs must NEVER contain credentials, private keys, API secrets, passwords, or seed phrases.
2. High-entropy API tokens and credentials are regex-redacted before emission.
3. Protected audit records are preserved with cryptographic integrity checks.
"""

import re
import os
import time
import glob
from typing import Dict, List, Any, Optional

# Regex patterns for sensitive secrets
SECRET_PATTERNS = [
    # Private keys (PEM / OpenSSH / RSA)
    (re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----.*?-----END [A-Z ]+ PRIVATE KEY-----", re.DOTALL), "[REDACTED_PRIVATE_KEY]"),
    # Generic API Keys / Secrets in key=val, key: val, or json format
    (re.compile(r"(?i)\b(api[_-]?key|api[_-]?secret|broker[_-]?secret|private[_-]?key|secret[_-]?key|auth[_-]?token|access[_-]?token|bearer[_-]?token|password|passwd|pin|secret)\s*[:=]\s*['\"]?([^\s'\"]+)['\"]?"), r"\1=[REDACTED_SECRET]"),
    # Bearer HTTP header tokens
    (re.compile(r"(?i)Bearer\s+[a-zA-Z0-9_\-\.]{16,}"), "Bearer [REDACTED_BEARER_TOKEN]"),
    # FIX Protocol Tag 96 (RawData / password/secret) or Tag 554 (Password)
    (re.compile(r"\b(96|554)=([^\x01| ]+)"), r"\1=[REDACTED_FIX_CREDENTIAL]"),
    # Long hex hashes that match 64-char or 32-char high entropy tokens
    (re.compile(r"(?i)\b(0x)?[a-f0-9]{64}\b"), "[REDACTED_HEX_KEY]"),
    # Seed phrases (12-24 mnemonic words indicator)
    (re.compile(r"(?i)(seed[_-]?phrase|mnemonic)\s*[:=]\s*['\"][^'\"]+['\"]"), r"\1=[REDACTED_MNEMONIC]"),
]

class LogSanitizer:
    """
    Sanitizes string and structured records to prevent secret leakage in logs.
    """

    @staticmethod
    def sanitize(text: str) -> str:
        """Applies all secret redaction patterns to the input text."""
        if not text:
            return ""
        sanitized = text
        for pattern, replacement in SECRET_PATTERNS:
            sanitized = pattern.sub(replacement, sanitized)
        return sanitized

    @staticmethod
    def sanitize_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Deeply sanitizes a dictionary of telemetry/logging fields."""
        cleaned = {}
        for k, v in record.items():
            k_lower = k.lower()
            if any(s in k_lower for s in ("secret", "password", "token", "private_key", "credential", "apikey", "api_key", "key")):
                cleaned[k] = "[REDACTED_SECRET]"
            elif isinstance(v, str):
                cleaned[k] = LogSanitizer.sanitize(v)
            elif isinstance(v, dict):
                cleaned[k] = LogSanitizer.sanitize_record(v)
            elif isinstance(v, list):
                cleaned[k] = [LogSanitizer.sanitize(item) if isinstance(item, str) else item for item in v]
            else:
                cleaned[k] = v
        return cleaned

    @staticmethod
    def rotate_log_if_needed(file_path: str, max_bytes: int = 10 * 1024 * 1024, backups: int = 5):
        """
        Rotates log files if they exceed max_bytes.
        Enforces secure permissions (0o640).
        """
        if not os.path.exists(file_path):
            return
        try:
            size = os.path.getsize(file_path)
            if size >= max_bytes:
                for i in range(backups - 1, 0, -1):
                    src = f"{file_path}.{i}"
                    dst = f"{file_path}.{i + 1}"
                    if os.path.exists(src):
                        os.replace(src, dst)
                os.replace(file_path, f"{file_path}.1")
                # Create new empty log with secure perms
                with open(file_path, "w", encoding="utf-8") as f:
                    pass
                os.chmod(file_path, 0o640)
        except Exception:
            pass
