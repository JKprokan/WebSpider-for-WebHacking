from setuptools import setup

setup(
    name="whspider",
    version="0.1.0",
    packages=["modules"],
    py_modules=["cli"],
    install_requires=[
        "click", 
    ],
    entry_points={
        "console_scripts": [
            "whspider = cli:webspider",
        ],
    },
)
