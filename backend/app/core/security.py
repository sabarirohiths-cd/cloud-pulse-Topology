import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from app.core.config import settings

STATIC_SALT = b"cloud_pulse_static_salt_value"

def _derive_key() -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=STATIC_SALT,
        iterations=100000,
    )
    return kdf.derive(settings.ENCRYPTION_KEY.encode('utf-8'))

def encrypt_credentials(credential_dict: dict) -> str:
    key = _derive_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    
    data = json.dumps(credential_dict).encode('utf-8')
    ciphertext = aesgcm.encrypt(nonce, data, None)
    
    combined = nonce + ciphertext
    return base64.urlsafe_b64encode(combined).decode('utf-8')

def decrypt_credentials(encrypted_str: str) -> dict:
    key = _derive_key()
    aesgcm = AESGCM(key)
    
    combined = base64.urlsafe_b64decode(encrypted_str.encode('utf-8'))
    nonce = combined[:12]
    ciphertext = combined[12:]
    
    data = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(data.decode('utf-8'))
