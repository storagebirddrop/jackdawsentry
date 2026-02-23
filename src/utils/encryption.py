"""
Jackdaw Sentry - Encryption Utilities

Centralized encryption and data protection utilities for secure data handling.
"""

import base64
import hashlib
import os
import secrets
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend


class EncryptionManager:
    """Centralized encryption management for Jackdaw Sentry"""
    
    def __init__(self, encryption_key: Optional[str] = None):
        """Initialize encryption manager
        
        Args:
            encryption_key: Base64 encoded encryption key. If None, generates new key.
        """
        if encryption_key:
            self.fernet = Fernet(encryption_key.encode())
            self._key = encryption_key
        else:
            self._key = self.generate_key()
            self.fernet = Fernet(self._key.encode())
    
    def generate_key(self) -> str:
        """Generate a new encryption key
        
        Returns:
            Base64 encoded encryption key
        """
        return Fernet.generate_key().decode()
    
    def encrypt(self, data: Union[str, bytes, Dict, List]) -> str:
        """Encrypt data
        
        Args:
            data: Data to encrypt
            
        Returns:
            Base64 encrypted string
        """
        if isinstance(data, (dict, list)):
            data = json.dumps(data, default=str).encode()
        elif isinstance(data, str):
            data = data.encode()
        
        encrypted = self.fernet.encrypt(data)
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> Union[str, Dict, List]:
        """Decrypt data
        
        Args:
            encrypted_data: Base64 encrypted string
            
        Returns:
            Decrypted data (str, dict, or list)
        """
        encrypted_bytes = base64.b64decode(encrypted_data.encode())
        decrypted = self.fernet.decrypt(encrypted_bytes)
        
        try:
            # Try to parse as JSON first
            return json.loads(decrypted.decode())
        except json.JSONDecodeError:
            # Return as string if not JSON
            return decrypted.decode()
    
    def get_key(self) -> str:
        """Get the current encryption key
        
        Returns:
            Base64 encoded encryption key
        """
        return self._key


# Global encryption manager instance
_encryption_manager: Optional[EncryptionManager] = None


def get_encryption_manager() -> EncryptionManager:
    """Get or create global encryption manager
    
    Returns:
        EncryptionManager instance
    """
    global _encryption_manager
    if _encryption_manager is None:
        # Try to get key from environment
        encryption_key = os.environ.get('ENCRYPTION_KEY')
        if encryption_key:
            _encryption_manager = EncryptionManager(encryption_key)
        else:
            # Generate new key and warn
            _encryption_manager = EncryptionManager()
            print(f"Generated new encryption key: {_encryption_manager.get_key()}")
            print("Set ENCRYPTION_KEY environment variable to persist encryption")
    
    return _encryption_manager


def encrypt_data(data: Union[str, bytes, Dict, List]) -> str:
    """Encrypt data using global encryption manager
    
    Args:
        data: Data to encrypt
        
    Returns:
        Base64 encrypted string
    """
    return get_encryption_manager().encrypt(data)


def decrypt_data(encrypted_data: str) -> Union[str, Dict, List]:
    """Decrypt data using global encryption manager
    
    Args:
        encrypted_data: Base64 encrypted string
        
    Returns:
        Decrypted data
    """
    return get_encryption_manager().decrypt(encrypted_data)


def hash_data(data: str, salt: Optional[str] = None) -> str:
    """Hash data using SHA-256
    
    Args:
        data: Data to hash
        salt: Optional salt for hashing
        
    Returns:
        Hexadecimal hash string
    """
    if salt:
        data = data + salt
    
    return hashlib.sha256(data.encode()).hexdigest()


def generate_secure_key(length: int = 32) -> str:
    """Generate cryptographically secure random key
    
    Args:
        length: Length of key in bytes
        
    Returns:
        Hexadecimal key string
    """
    return secrets.token_hex(length)


def derive_key_from_password(password: str, salt: str, iterations: int = 100000) -> str:
    """Derive encryption key from password using PBKDF2
    
    Args:
        password: Password to derive key from
        salt: Salt for key derivation
        iterations: Number of PBKDF2 iterations
        
    Returns:
        Base64 derived key
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt.encode(),
        iterations=iterations,
        backend=default_backend()
    )
    key = kdf.derive(password.encode())
    return base64.urlsafe_b64encode(key).decode()


def mask_sensitive_data(data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
    """Mask sensitive data for logging/display
    
    Args:
        data: Sensitive data to mask
        mask_char: Character to use for masking
        visible_chars: Number of characters to keep visible at start/end
        
    Returns:
        Masked data string
    """
    if len(data) <= visible_chars * 2:
        return mask_char * len(data)
    
    if len(data) <= visible_chars * 2 + 2:
        return data[:visible_chars] + mask_char * (len(data) - visible_chars * 2)
    
    return (
        data[:visible_chars] + 
        mask_char * (len(data) - visible_chars * 2) + 
        data[-visible_chars:]
    )


def verify_data_integrity(data: str, expected_hash: str) -> bool:
    """Verify data integrity using hash comparison
    
    Args:
        data: Data to verify
        expected_hash: Expected hash value
        
    Returns:
        True if data integrity is verified
    """
    actual_hash = hash_data(data)
    return actual_hash == expected_hash


def create_data_checksum(data: Union[str, Dict, List]) -> str:
    """Create checksum for data integrity verification
    
    Args:
        data: Data to create checksum for
        
    Returns:
        Hexadecimal checksum
    """
    if isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True, default=str)
    
    return hashlib.sha256(data.encode()).hexdigest()


def secure_compare(a: str, b: str) -> bool:
    """Secure string comparison to prevent timing attacks
    
    Args:
        a: First string
        b: Second string
        
    Returns:
        True if strings are equal
    """
    return secrets.compare_digest(a.encode(), b.encode())


def generate_nonce(length: int = 16) -> str:
    """Generate cryptographic nonce
    
    Args:
        length: Length of nonce in bytes
        
    Returns:
        Hexadecimal nonce string
    """
    return secrets.token_hex(length)


class DataMasker:
    """Utility class for masking different types of sensitive data"""
    
    @staticmethod
    def mask_email(email: str) -> str:
        """Mask email address
        
        Args:
            email: Email address to mask
            
        Returns:
            Masked email
        """
        if '@' not in email:
            return mask_sensitive_data(email)
        
        local, domain = email.split('@', 1)
        if len(local) <= 2:
            masked_local = mask_sensitive_data(local, visible_chars=1)
        else:
            masked_local = local[0] + '*' * (len(local) - 2) + local[-1]
        
        return f"{masked_local}@{domain}"
    
    @staticmethod
    def mask_phone(phone: str) -> str:
        """Mask phone number
        
        Args:
            phone: Phone number to mask
            
        Returns:
            Masked phone number
        """
        # Remove non-numeric characters
        clean_phone = ''.join(c for c in phone if c.isdigit())
        
        if len(clean_phone) <= 4:
            return mask_sensitive_data(phone, visible_chars=2)
        
        return clean_phone[:2] + '*' * (len(clean_phone) - 4) + clean_phone[-2:]
    
    @staticmethod
    def mask_credit_card(card_number: str) -> str:
        """Mask credit card number
        
        Args:
            card_number: Credit card number to mask
            
        Returns:
            Masked credit card number
        """
        # Remove spaces and dashes
        clean_card = ''.join(c for c in card_number if c.isdigit())
        
        if len(clean_card) < 4:
            return mask_sensitive_data(card_number)
        
        return '*' * (len(clean_card) - 4) + clean_card[-4:]
    
    @staticmethod
    def mask_address(address: str) -> str:
        """Mask address for privacy
        
        Args:
            address: Address to mask
            
        Returns:
            Masked address
        """
        parts = address.split(',')
        if len(parts) <= 2:
            return mask_sensitive_data(address, visible_chars=3)
        
        # Keep first part (street number and first few chars)
        street = parts[0].strip()
        if len(street) <= 5:
            masked_street = mask_sensitive_data(street, visible_chars=2)
        else:
            masked_street = street[:5] + '*' * (len(street) - 5)
        
        return masked_street + ', ' + ', '.join(parts[1:])


# Convenience functions for common masking operations
def mask_email(email: str) -> str:
    """Mask email address"""
    return DataMasker.mask_email(email)


def mask_phone(phone: str) -> str:
    """Mask phone number"""
    return DataMasker.mask_phone(phone)


def mask_credit_card(card_number: str) -> str:
    """Mask credit card number"""
    return DataMasker.mask_credit_card(card_number)


def mask_address(address: str) -> str:
    """Mask address"""
    return DataMasker.mask_address(address)
