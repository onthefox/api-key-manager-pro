from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="api-key-manager-pro",
    version="1.0.0",
    author="API Key Manager Team",
    author_email="support@example.com",
    description="Production-ready async API key manager with Flask dashboard and HMAC-SHA256 validation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/onthefox/api-key-manager-pro",
    packages=find_packages(exclude=["tests", "examples", "docker"]),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.9.0",
        "aiofiles>=23.2.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.5.0",
        "Flask>=3.0.0",
        "cryptography>=41.0.0",
    ],
    extras_require={
        "vault": ["hvac>=1.2.0"],
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "api-key-manager=core.cli:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)
