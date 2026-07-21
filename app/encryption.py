"""
Authenticated encryption utilities for NotifyHub.

Algorithm: AES-256-GCM
  - Provides both confidentiality AND integrity (authenticated encryption).
  - Immune to padding oracle attacks that affect AES-CBC without a MAC.
  - Each encryption call generates a random 96-bit IV (nonce); ciphertext
    format: <iv_hex>:<tag_hex>:<ciphertext_hex> — three colon-separated parts.

CWE-327 mitigation: AES-CBC without authentication is explicitly NOT used here.
The three-part format allows the decrypt function to reject any ciphertext that
does not carry a GCM auth tag, preventing legacy CBC bypass (two-part format
with only iv:ciphertext would raise ValueError at the split/length check).
"""

import os
import hashlib
import hmac
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_key() -> bytes:
    """Return the 32-byte AES key from settings."""
    from django.conf import settings
    raw = getattr(settings, 'FIELD_ENCRYPTION_KEY', '') or ''
    if not raw:
        raise ValueError('FIELD_ENCRYPTION_KEY is not configured.')
    # FIELD_ENCRYPTION_KEY is a Fernet key (URL-safe base64, 44 chars).
    # Derive a 32-byte AES key from it deterministically via SHA-256 so the
    # two subsystems (Fernet fields, AES-GCM utils) share one env var.
    import base64
    try:
        key_bytes = base64.urlsafe_b64decode(raw + '==')
    except Exception:
        key_bytes = raw.encode()
    return hashlib.sha256(key_bytes).digest()   # always 32 bytes


def encrypt(plaintext: str) -> str:
    """
    Encrypt *plaintext* with AES-256-GCM and return an authenticated ciphertext
    string in the form  <iv_hex>:<tag_hex>:<ciphertext_hex>.

    The 16-byte GCM authentication tag is stored explicitly so that decrypt()
    can verify it before returning any plaintext — there is no unauthenticated
    path.
    """
    key = _get_key()
    iv = os.urandom(12)                         # 96-bit nonce recommended for GCM
    aesgcm = AESGCM(key)
    # AESGCM.encrypt() appends the 16-byte tag to the ciphertext
    ct_with_tag = aesgcm.encrypt(iv, plaintext.encode(), None)
    ciphertext = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    return f"{iv.hex()}:{tag.hex()}:{ciphertext.hex()}"


def decrypt(token: str) -> str:
    """
    Decrypt a ciphertext produced by encrypt().

    Raises ValueError for any input that is not a valid three-part
    AES-256-GCM token — including two-part AES-CBC style ciphertexts, which
    are rejected before any decryption is attempted (CWE-327 / padding oracle
    mitigation).
    """
    parts = token.split(':')
    if len(parts) != 3:
        # Explicitly reject two-part (iv:ciphertext) CBC-style tokens.
        raise ValueError(
            'Invalid ciphertext format — expected iv:tag:ciphertext (AES-256-GCM). '
            'Two-part AES-CBC ciphertexts are not accepted.'
        )
    iv_hex, tag_hex, ct_hex = parts
    try:
        iv = bytes.fromhex(iv_hex)
        tag = bytes.fromhex(tag_hex)
        ciphertext = bytes.fromhex(ct_hex)
    except ValueError:
        raise ValueError('Ciphertext contains invalid hex data.')

    if len(iv) != 12:
        raise ValueError('IV must be 12 bytes for AES-256-GCM.')
    if len(tag) != 16:
        raise ValueError('Authentication tag must be 16 bytes.')

    key = _get_key()
    aesgcm = AESGCM(key)
    # Recombine ciphertext + tag as AESGCM.decrypt() expects
    ct_with_tag = ciphertext + tag
    try:
        plaintext = aesgcm.decrypt(iv, ct_with_tag, None)
    except Exception:
        # cryptography raises InvalidTag on auth failure — surface as ValueError
        raise ValueError('Decryption failed: authentication tag mismatch or corrupted ciphertext.')
    return plaintext.decode()
