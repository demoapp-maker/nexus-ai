from cryptography.fernet import Fernet
from logic.secrets import decrypt_secret, encrypt_secret


def test_provider_secret_is_encrypted_at_rest(monkeypatch):
    monkeypatch.setenv("NEXUS_CONFIG_ENCRYPTION_KEY", Fernet.generate_key().decode())
    encrypted = encrypt_secret("provider-secret")
    assert encrypted.startswith("fernet:v1:")
    assert "provider-secret" not in encrypted
    assert decrypt_secret(encrypted) == "provider-secret"
