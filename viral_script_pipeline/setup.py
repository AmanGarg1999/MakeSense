from setuptools import setup, find_packages

setup(
    name="viral-script-pipeline",
    version="1.0.0",
    description="Viral YouTube script generation pipeline with multi-framework support and scoring",
    author="Hermes Agent",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "openai>=1.0.0",
        "anthropic>=0.7.0",
        "jsonschema>=4.0.0",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": ["pytest", "black", "ruff"],
    },
    entry_points={
        "console_scripts": [
            "viral-script=viral_script_pipeline.main:run_demo",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)