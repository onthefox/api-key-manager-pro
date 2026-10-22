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
- 🔐 **HMAC-SHA256 Validation** - Cryptographically secure signature generation and verification. Signatures are computed over `"{key}:{timestamp}"`, binding every request to its timestamp and preventing replay of captured requests beyond the validation window. Use the reference helper `core.sign_request(key, secret, timestamp)` on the client side.
- 🛡️ **Constant-Time Comparison** - Prevents timing attacks using `hmac.compare_digest()`
- 🔄 **Configurable Validation Windows** - 5 minutes to 30+ days (default: 6 hours)
- ⏱️ **Clock Skew Tolerance** - Configurable tolerance (default: 60 seconds) for distributed systems
- 🧯 **Fail-Fast Configuration** - `Settings.validate()` refuses to boot with a missing `SECRET_KEY` outside DEBUG mode (no hardcoded default).

### Advanced Features
- 📦 **Modular Architecture** - Clean separation of concerns, easily extensible
- 🗃️ **Bounded LRU Validation Cache** - Memory-safe under adversarial load; `validator.invalidate_key()` / key revocation purge cached approvals immediately.

## 🚀 Quick Start

```python
import time
from core import KeyManager, sign_request

manager = KeyManager()

# 1. Register a key (the plaintext secret is never echoed back)
await manager.create_key("client-1", secret="<random-secret>", metadata={"tier": "gold"})

# 2. Client signs key + timestamp
ts = int(time.time())
signature = sign_request("client-1", "<random-secret>", ts)

# 3. Server validates
ok = await manager.validate_key("client-1", signature, timestamp=ts)  # True

# 4. Revocation takes effect immediately (cached validations purged)
await manager.revoke_key("client-1")  # subsequent validate_key -> KeyRevokedError
```

Run tests: `pip install pytest pytest-asyncio && python -m pytest tests/`

---

<div align="center">

**onthefox** • Bridge Builder • Cross-Chain Architect

```
  /\_/\  
 ( 😎‿😎) 
 (  💻  ) 
 /|     |\ 
/_|     |_\
```

**KOTEBALTVOYROT**

![Stars](https://img.shields.io/github/stars/onthefox/api-key-manager-pro?style=flat&logo=github&color=orange)
![License](https://img.shields.io/github/license/onthefox/api-key-manager-pro?style=flat&color=blue)
![Topics](https://img.shields.io/github/topics/onthefox/api-key-manager-pro?style=flat)

*Built with* 🔥 *by onthefox*

</div>
