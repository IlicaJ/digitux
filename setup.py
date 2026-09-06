"""Setup for pip / stdeb builds.

Defines the `digitux` entry point and packages the bundled assets/data so the
frozen binary, `.deb` and `pip install` all resolve resources via `runtime.py`.
"""
import glob
from setuptools import setup, find_packages

setup(
    name="digitux",
    version="0.2.0",
    description="DigiTux — RP360/RP360XP editor for Linux",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="IlicaJ",
    url="https://github.com/IlicaJ/digitux",
    license="GPL-3.0",
    packages=find_packages(include=["nexus", "nexus.*"]),
    include_package_data=True,
    package_data={
        "nexus": [
            "rp360_effects.json",
            "data/*.json",
            "assets/img/**/*.png",
            "assets/img/**/*.jpeg",
            "assets/img/**/*.jpg",
        ],
    },
    data_files=[
        ("share/icons/hicolor/256x256/apps", ["packaging/digitux.png"]),
        ("share/applications", ["packaging/digitux.desktop"]),
        ("lib/udev/rules.d", ["packaging/99-rp360.rules"]),
    ],
    entry_points={
        "console_scripts": [
            "digitux=nexus.ui.main:main",
        ],
    },
    install_requires=[
        "pyserial>=3.5",
        "PyQt5>=5.15",
    ],
    python_requires=">=3.9",
)