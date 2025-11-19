# API Key Manager Pro

> **Production-ready async API key management system** with HMAC-SHA256 validation, caching, audit logging, and optional Vault integration.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Async Ready](https://img.shields.io/badge/Async-Ready-green)](https://docs.python.org/3/library/asyncio.html)
[![Code Style: Black](https://img.shields.io/badge/Code%20Style-Black-black)](https://github.com/psf/black)

## 🎯 Overview

API Key Manager Pro is a battle-tested async API key validation system designed for **high-performance, distributed environments**. It provides enterprise-grade security, automatic key expiration, comprehensive audit trails, and seamless integration with HashiCorp Vault.

### Why Choose API Key Manager Pro?

- **Zero-Trust Security** - Cryptographic signature verification using HMAC-SHA256 with constant-time comparison (prevents timing attacks)
- **Distributed-Ready** - Clock skew tolerance and configurable validation windows for multi-region deployments
- **Performance Optimized** - Built-in caching, batch operations, and async-first architecture
- **Production-Grade** - Comprehensive error handling, retry logic, detailed logging, and metrics
- **Developer Friendly** - Clean API, extensive documentation, Docker support, and practical examples

## ✨ Features

### Core Security
- ⚡ **Async/Await Architecture** - Non-blocking operations leveraging `asyncio` for concurrent processing
- 🔐 **HMAC-SHA256 Validation** - Cryptographically secure signature generation and verification
- 🛡️ **Constant-Time Comparison** - Prevents timing attacks using `hmac.compare_digest()`
- 🔄 **Configurable Validation Windows** - 5 minutes to 30+ days (default: 6 hours)
- ⏱️ **Clock Skew Tolerance** - Configurable tolerance (default: 60 seconds) for distributed systems

### Advanced Features
- 📦 **Modular Architecture** - Clean separation of concerns, easily extensible
- 🎯 **Batch Operations** - Validate multiple keys concurrently with `asyncio.gather()`
- 💾 **Smart Caching** - Automatic result caching with TTL (configurable)
- 📝 **Audit Logging** - Complete operation history with timestamps and actions
- 🔗 **Vault Integration** - Optional HashiCorp Vault for secret management
- 📊 **Metrics & Reporting** - Built-in cache statistics and key management insights
- 🔄 **Automatic Expiration** - Keys expire outside validation window automatically
- 🚀 **Rate Limiting Ready** - Framework for implementing rate limiting strategies

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/onthefox/api-key-manager-pro.git
cd api-key-manager-pro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt
```

### Using Docker (Recommended)

```bash
# Start with docker-compose (includes Vault)
docker-compose up -d

# Or build and run manually
docker build -f docker/Dockerfile -t api-key-manager:latest .
docker run -p 5000:5000 api-key-manager:latest
```

## 💡 Usage Examples

### Basic Validation

```python
import asyncio
from core import AsyncAPIKeyValidator

async def validate_key():
    validator = AsyncAPIKeyValidator(
        validation_window_minutes=360,  # 6 hours
        clock_skew_tolerance_seconds=60
    )
    
    # Validate a key signature
    try:
        is_valid = await validator.validate(
            key="my-api-key",
            signature="abc123def456...",
            secret="my-secret-key"
        )
        print(f"Key valid: {is_valid}")
    except Exception as e:
        print(f"Validation error: {e}")

asyncio.run(validate_key())
```

### Key Lifecycle Management

```python
import asyncio
from core import KeyManager, AsyncAPIKeyValidator

async def manage_keys():
    # Initialize manager with validator
    validator = AsyncAPIKeyValidator()
    manager = KeyManager(validator)
    
    # Create a new key
    key = await manager.create_key(
        key_id="client-123",
        secret="super-secret-key",
        metadata={"client_name": "Acme Corp", "tier": "premium"}
    )
    print(f"Created key: {key['key_id']}")
    
    # Validate the key
    is_valid = await manager.validate_key(
        key_id="client-123",
        signature="abc123def456..."
    )
    
    # List active keys
    active_keys = manager.list_keys(active_only=True)
    print(f"Active keys: {len(active_keys)}")
    
    # Revoke a key
    await manager.revoke_key("client-123")
    print("Key revoked")
    
    # Get audit log
    audit_log = manager.get_audit_log()
    print(f"Operations logged: {len(audit_log)}")

asyncio.run(manage_keys())
```

### Batch Operations

```python
import asyncio
from core import AsyncAPIKeyValidator

async def batch_validate():
    validator = AsyncAPIKeyValidator()
    
    validations = [
        {"key": "key-1", "signature": "sig1", "secret": "secret1"},
        {"key": "key-2", "signature": "sig2", "secret": "secret2"},
        {"key": "key-3", "signature": "sig3", "secret": "secret3"},
    ]
    
    # Validate all keys concurrently
    results = await validator.batch_validate(validations)
    
    for i, result in enumerate(results):
        print(f"Key {i+1}: {'Valid' if result else 'Invalid'}")

asyncio.run(batch_validate())
```

## ⚙️ Configuration

Environment variables can be set via `.env` file or system environment:

```bash
# Validation
VALIDATION_WINDOW_MINUTES=360          # Default: 6 hours
CLOCK_SKEW_TOLERANCE_SECONDS=60        # Default: 60 seconds

# Application
DEBUG=false
LOG_LEVEL=INFO

# Vault (Optional)
VAULT_ENABLED=false
VAULT_ADDR=http://127.0.0.1:8200
VAULT_TOKEN=dev-token
VAULT_NAMESPACE=kv

# Caching
CACHE_TTL_SECONDS=300

# Rate Limiting
RATE_LIMIT_ENABLED=false
RATE_LIMIT_PER_MINUTE=100
```

Load configuration in Python:

```python
from config import Settings

# Access settings
print(f"Validation window: {Settings.VALIDATION_WINDOW_MINUTES} minutes")
print(f"Vault enabled: {Settings.VAULT_ENABLED}")
```

## 🔐 Security Best Practices

### Never Commit Secrets

```python
# ❌ DON'T
VAULT_TOKEN = "hvs.CAESICJfnH4Km1..."

# ✅ DO
VAULT_TOKEN = os.getenv("VAULT_TOKEN")
```

### Use Constant-Time Comparison

All signature verifications use `hmac.compare_digest()` to prevent timing attacks:

```python
# Internally handled - never exposed
if not hmac.compare_digest(expected_sig, provided_sig):
    raise InvalidSignatureError()
```

### Validate Timestamps

```python
# Clock skew tolerance prevents distributed system issues
validator = AsyncAPIKeyValidator(
    clock_skew_tolerance_seconds=60  # Tolerates 1 minute of clock drift
)
```

### Audit Everything

```python
# All operations logged automatically
audit_log = manager.get_audit_log()
for entry in audit_log:
    print(f"{entry['timestamp']} - {entry['action']}: {entry['key_id']}")
```

## 📚 API Reference

### AsyncAPIKeyValidator

```python
class AsyncAPIKeyValidator:
    async def validate(
        key: str,
        signature: str,
        secret: str,
        timestamp: Optional[int] = None,
        use_cache: bool = True
    ) -> bool: ...
    
    async def batch_validate(
        validations: list[Dict[str, str]]
    ) -> list[bool]: ...
    
    def clear_cache() -> None: ...
    def get_cache_stats() -> Dict[str, int]: ...
```

### KeyManager

```python
class KeyManager:
    async def create_key(
        key_id: str,
        secret: str,
        metadata: Optional[Dict] = None
    ) -> Dict: ...
    
    async def validate_key(
        key_id: str,
        signature: str,
        timestamp: Optional[int] = None
    ) -> bool: ...
    
    async def revoke_key(key_id: str) -> bool: ...
    async def get_key(key_id: str) -> Dict: ...
    async def batch_validate(validations: List[Dict]) -> List[Dict]: ...
    
    def list_keys(active_only: bool = True) -> List[Dict]: ...
    def get_audit_log() -> List[Dict]: ...
```

## 🏗️ Architecture

```
api-key-manager-pro/
├── core/                    # Core validation & management
│   ├── validator.py        # AsyncAPIKeyValidator (HMAC-SHA256)
│   ├── manager.py          # KeyManager lifecycle
│   └── exceptions.py       # Custom exceptions
├── config/                  # Configuration management
│   └── settings.py         # Environment-based settings
├── vault_integration/       # Optional Vault support
│   └── vault_client.py    # Vault secret storage
├── examples/               # Usage examples
├── tests/                  # Test suite
├── docker/                 # Docker configuration
│   └── Dockerfile         # Production container
└── docker-compose.yml      # Local development stack
```

## 🔄 Workflow Example

```
1. Client generates signature: HMAC-SHA256(key, secret)
   ↓
2. Sends: {key, signature, timestamp}
   ↓
3. Manager retrieves secret from storage/Vault
   ↓
4. Validator checks timestamp within window
   ↓
5. Validator recalculates signature (constant-time comparison)
   ↓
6. If valid → Success (log audit entry, update last_used)
   If invalid → Failure (log attempt, raise exception)
   ↓
7. Return: {valid: true/false, cached: true/false}
```

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=core --cov-report=html

# Specific test file
pytest tests/test_validator.py -v
```

## 🌐 Integration with Vault

```python
from vault_integration import VaultClient
from config import Settings

# Optional: Use Vault for secret storage
if Settings.VAULT_ENABLED:
    vault = VaultClient(
        address=Settings.VAULT_ADDR,
        token=Settings.VAULT_TOKEN
    )
    secret = vault.get_secret("api-keys", "client-123")
```

## 📊 Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Single validation | ~0.1ms | HMAC-SHA256 | 
| Batch (100 keys) | ~5ms | Concurrent |
| Cache hit | <0.01ms | In-memory |
| Cache miss | ~0.1ms | Full validation |

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Roadmap

- [ ] WebSocket support for real-time validation
- [ ] Redis integration for distributed caching
- [ ] Prometheus metrics export
- [ ] GraphQL API
- [ ] Rate limiting middleware
- [ ] Key rotation automation
- [ ] Migration tools from existing systems

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙋 Support

- 📖 [Full Documentation](docs/)
- 🐛 [Report Issues](https://github.com/onthefox/api-key-manager-pro/issues)
- 💬 [Discussions](https://github.com/onthefox/api-key-manager-pro/discussions)
- 📧 Email: support@example.com

## 👨‍💼 About

Built with ❤️ for developers who care about **security, performance, and clean code**.
