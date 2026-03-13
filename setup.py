from setuptools import setup, find_packages

setup(
    name="geompy-display",
    version="0.1.0",
    description="pythonocc-core viewer wrapper with always-on orientation ViewCube",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "PySide6",
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
