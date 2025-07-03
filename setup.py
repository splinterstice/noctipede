from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="noctipede",
    version="1.0.0",
    author="Noctipede Development Team",
    description="A modular, scalable system for crawling, analyzing, and reporting on deep web content",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.11",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "noctipede-crawler=noctipede.crawlers.main:main",
            "noctipede-portal=noctipede.portal.main:main",
            "noctipede-analyzer=noctipede.analysis.image_analyzer:main",
            "noctipede-moderator=noctipede.analysis.content_moderator:main",
        ],
    },
)
