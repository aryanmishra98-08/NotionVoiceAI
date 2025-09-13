from setup_loader_app import config_data, logger
import jwt
import time
from pathlib import Path
from typing import Dict
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from .DynamoDBManager import DynamoDBManager

# Extract configuration values
jwt_algorithm = config_data['jwt_authentication']['algorithm']
access_token_expire_minutes = int(
    config_data['jwt_authentication']['access_token_expire_minutes']
)

# Placeholders for PBKDF2 salt-based decryption
password_placeholder = config_data['decryption']['password_placeholder']
salt_placeholder = config_data['decryption']['salt_placeholder']

# AWS Configuration
region_name = config_data['aws']['region']
service_account_table_name = config_data['aws']['dynamodb']['service_account_records_table']
call_records_table_name = config_data['aws']['dynamodb']['call_records_table']

# Load RSA keys for JWT signing and verification
SERVICE_ACCOUNT_CALL_PRIVATE_KEY = Path(
    config_data['jwt_authentication']['service_acc_and_call_id_private_key_path']
).read_text()
SERVICE_ACCOUNT_CALL_PUBLIC_KEY = Path(
    config_data['jwt_authentication']['service_acc_and_call_id_public_key_path']
).read_text()

# Initialize Fernet cipher for symmetric encryption
ENCRYPTION_KEY = config_data['encryption']['key'].encode()
fernet_cipher = Fernet(ENCRYPTION_KEY)

# Initialize Managers
service_account_db_manager = DynamoDBManager(
    region_name, service_account_table_name
)
call_records_db_manager = DynamoDBManager(
    region_name, call_records_table_name
)


def encrypt_value(value: str) -> str:
    """
    Encrypt plaintext using Fernet symmetric encryption.

    Args:
        value (str): The plaintext string to encrypt.

    Returns:
        str: The encrypted string as URL-safe base64.
    """
    encrypted_bytes = fernet_cipher.encrypt(value.encode())
    encrypted_text = encrypted_bytes.decode()
    logger.debug(f"encrypt_value: Encrypted value of length {len(value)}")
    return encrypted_text


def decrypt_value(token: str) -> str:
    """
    Decrypt a Fernet-encrypted string back to plaintext.

    Args:
        token (str): The URL-safe base64 encrypted string.

    Returns:
        str: The decrypted plaintext string.
    """
    decrypted_bytes = fernet_cipher.decrypt(token.encode())
    decrypted_text = decrypted_bytes.decode()
    logger.debug(f"decrypt_value: Decrypted token of length {len(token)}")
    return decrypted_text


def generate_key(password: bytes, salt: bytes) -> bytes:
    """
    Derive a 32-byte key via PBKDF2-HMAC-SHA256 from password and salt.

    Args:
        password (bytes): The password bytes.
        salt (bytes): The salt bytes.

    Returns:
        bytes: The derived encryption key.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        salt=salt,
        length=32,
        iterations=100000,
        backend=default_backend()
    )
    derived_key = kdf.derive(password)
    logger.debug("generate_key: Derived key using PBKDF2-HMAC-SHA256")
    return derived_key


def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """
    AES-CFB decrypt: first 16 bytes = IV, rest = ciphertext.

    Args:
        encrypted_data (bytes): The IV + ciphertext.
        key (bytes): The AES key.

    Returns:
        bytes: The decrypted plaintext bytes.
    """
    iv = encrypted_data[:16]
    ciphertext = encrypted_data[16:]
    cipher_obj = Cipher(
        algorithms.AES(key),
        modes.CFB(iv),
        backend=default_backend()
    )
    decryptor = cipher_obj.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()
    logger.debug(
        f"decrypt_data: Decrypted ciphertext of length {len(ciphertext)}")
    return plaintext


def decrypt_data_result(encrypted_data_hex: str) -> str:
    """
    Hex-to-bytes + PBKDF2-derived-key + AES-CFB decrypt to plaintext.

    Args:
        encrypted_data_hex (str): The hex-encoded encrypted payload.

    Returns:
        str: The decrypted plaintext string.
    """
    password_bytes = password_placeholder.encode()
    salt_bytes = salt_placeholder.encode()
    key = generate_key(password_bytes, salt_bytes)
    raw_bytes = bytes.fromhex(encrypted_data_hex)
    decrypted_bytes = decrypt_data(raw_bytes, key)
    plaintext = decrypted_bytes.decode()
    logger.debug("decrypt_data_result: Completed full decryption pipeline")
    return plaintext


def sign_jwt_with_service_acc_and_call_id(user_id: str, call_id: str, caller_id: str) -> Dict[str, str]:
    """
    Sign a JWT with both encrypted user_id and call_id,
    using the combined service account and call-private key.

    Args:
        user_id (str): The service account identifier.
        call_id (str): The call record identifier.
        caller_id (str): The caller identifier.

    Returns:
        Dict[str, str]: A dict with 'access_token', or empty dict on failure.
    """
    try:
        encrypted_user = encrypt_value(user_id)
        encrypted_call = encrypt_value(call_id)
        encrypted_caller = encrypt_value(caller_id)
        expiration_time = time.time() + (access_token_expire_minutes * 60)
        payload = {
            "user_id": encrypted_user,
            "ccaas_call_id": encrypted_call,
            "caller_id": encrypted_caller,
            "exp": expiration_time,
        }
        token = jwt.encode(
            payload,
            SERVICE_ACCOUNT_CALL_PRIVATE_KEY,
            algorithm=jwt_algorithm
        )
        logger.info(
            f"[AccAndCallID] Signed JWT for user_id={user_id}, call_id={call_id}")
        return {"access_token": token}
    except Exception as e:
        logger.exception(
            f"[AccAndCallID] JWT signing failed for user_id={user_id}, call_id={call_id}: {e}")
        return {}


def decode_jwt_with_service_acc_and_call_id(token: str) -> dict:
    """
    Decode & verify an AccAndCallID JWT, decrypt both user_id and call_id.

    Args:
        token (str): The JWT string to decode.

    Returns:
        dict: The decoded payload with decrypted 'user_id' and 'call_id', or empty dict on error.
    """
    try:
        data = jwt.decode(
            token,
            SERVICE_ACCOUNT_CALL_PUBLIC_KEY,
            algorithms=[jwt_algorithm]
        )
        if "user_id" in data:
            data["user_id"] = decrypt_value(data["user_id"])
        if "ccaas_call_id" in data:
            data["ccaas_call_id"] = decrypt_value(data["ccaas_call_id"])
        if "caller_id" in data:
            data["caller_id"] = decrypt_value(data["caller_id"])
        logger.info("[AccAndCallID] Successfully decoded JWT")
        return data
    except jwt.ExpiredSignatureError:
        logger.exception("[AccAndCallID] JWT token has expired.")
        return {}
    except jwt.InvalidTokenError as e:
        logger.exception(f"[AccAndCallID] Invalid JWT token: {e}")
        return {}


class JWTBearerWithServiceAccAndCallID(HTTPBearer):
    """
    HTTPBearer for call-and-account endpoints: validates both IDs.
    """

    def __init__(self, auto_error: bool = True):
        super(JWTBearerWithServiceAccAndCallID,
              self).__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> str:
        """
        Extract the JWT from Authorization header for call endpoints.

        Raises HTTPException if missing or invalid.
        """
        creds: HTTPAuthorizationCredentials = await super(JWTBearerWithServiceAccAndCallID, self).__call__(request)
        if creds:
            return creds.credentials
        logger.error("[AccAndCallID] Missing authorization header.")
        raise HTTPException(
            status_code=403,
            detail="Authorization required."
        )

    def verify_jwt(self, token: str, user_id: str, ccaas_call_id: str, db_manager: DynamoDBManager = call_records_db_manager) -> bool:
        """
        Verify AccAndCallID JWT, decrypt IDs, and check each in DynamoDB.

        Args:
            token (str): The JWT to verify.
            user_id (str): The expected user identifier.
            ccaas_call_id (str): The expected call record identifier.
            db_manager (DynamoDBManager): Manager for call records table.

        Returns:
            bool: True if both IDs match records; False otherwise.
        """
        try:
            payload = decode_jwt_with_service_acc_and_call_id(token)
            decrypted_user_id = payload.get("user_id")
            decrypted_call_id = payload.get("ccaas_call_id")
            decrypted_caller_id = payload.get("caller_id")

            logger.info(
                f"[AccAndCallID] Verifying JWT for user_id={decrypted_user_id}, call_id={decrypted_call_id}, caller_id={decrypted_caller_id}")

            user_record = service_account_db_manager.get_item_by_id(
                {"service_account_id": decrypted_user_id})
            logger.debug(f"[AccAndCallID] Retrieved user_record: {user_record}")
            if not (user_record.get("status") and user_record.get("output")):
                logger.info(
                    f"[AccAndCallID] Unknown user_id: {decrypted_user_id}")
                return False

            user_record_id = user_record['output'].get('service_account_id', '')
            if user_record_id != user_id:
                logger.info(
                    f"[AccAndCallID] User ID mismatch: {user_record_id} != {user_id}")
                return False

            call_record = db_manager.get_item_by_id(
                {"ccaas_call_id": decrypted_call_id})
            logger.debug(
                f"[AccAndCallID] Retrieved call_record: {call_record}")
            if not (call_record.get("status") and call_record.get("output")):
                logger.info(
                    f"[AccAndCallID] Unknown ccaas_call_id: {decrypted_call_id}")
                return False
            call_record_id = call_record.get('output', {}).get('ccaas_call_id', '')
            caller_id = call_record.get('output', {}).get('caller_id', '')
            if call_record_id != ccaas_call_id:
                logger.info(
                    f"[AccAndCallID] Call ID mismatch: {call_record_id} != {ccaas_call_id}")
                return False
            if caller_id != decrypted_caller_id:
                logger.info(
                    f"[AccAndCallID] Caller ID mismatch: {caller_id} != {decrypted_caller_id}")
                return False

            logger.info(
                f"[AccAndCallID] JWT verification succeeded for user_id={decrypted_user_id}, call_id={decrypted_call_id}, caller_id={decrypted_caller_id}")
            return True
        except Exception as e:
            logger.exception(f"[AccAndCallID] JWT verification error: {e}")
            return False
