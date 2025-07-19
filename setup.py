from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="cloudarb",
    version="1.0.0",
    author="CloudArb Team",
    author_email="siddhantkhare2694@gmail.com",
    description="GPU Arbitrage Platform for Cloud Cost Optimization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Siddhant-K-code/cloudarb",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "pytest-asyncio>=0.21.1",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "isort>=5.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
        ],
        "ml": [
            "scikit-learn>=1.3.2",
            "prophet>=1.1.4",
            "xgboost>=2.0.2",
            "lightgbm>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "cloudarb=cloudarb.main:main",
            "cloudarb-optimize=cloudarb.optimization.cli:main",
            "cloudarb-ingest=cloudarb.ingestion.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "cloudarb": ["py.typed"],
    },
)