from setuptools import setup, find_packages

setup(
    name="unified-proxy-collector",
    version="1.0.0",
    description="A unified high-performance proxy collector merging features from V2Ray-Collector, TG-Parser, and Telegram-Configs-Collector.",
    packages=find_packages(),
    install_requires=[
        "beautifulsoup4>=4.9.0",
        "requests>=2.28.0",
        "tqdm>=4.64.0",
        "wget",
        "jdatetime",
        "tldextract",
        "geoip2",
        "dnspython",
        "pycountry_convert",
        "rich>=13.0.0",
        "colorama>=0.4.6"
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "unified-collector=main:main",
        ],
    },
)
