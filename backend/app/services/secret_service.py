"""Secret management service - encrypt/decrypt API keys."""
import logging
from cryptography.fernet import Fernet
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_fernet = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        settings = get_settings()
        # Use the independent ENCRYPTION_KEY (not derived from JWT_SECRET)
        if not settings.ENCRYPTION_KEY:
            raise RuntimeError("ENCRYPTION_KEY 未配置")
        _fernet = Fernet(settings.ENCRYPTION_KEY.encode())
    return _fernet


def encrypt_key(plaintext: str) -> str:
    """Encrypt an API key."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """Decrypt an API key."""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def mask_key(plaintext: str) -> str:
    """Show only last 4 chars: sk-****abcd."""
    if len(plaintext) <= 4:
        return "****"
    return "****" + plaintext[-4:]


def key_suffix(plaintext: str) -> str:
    """Get last 4 chars for display."""
    return plaintext[-4:] if len(plaintext) >= 4 else plaintext
