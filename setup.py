from setuptools import setup

setup(
    name="whspider",
    version="0.1.0",
    packages=["modules"],
    py_modules=["cli"],
    install_requires=[
        "click",    # click 쓰니까 필수
        # 기타 필요한 패키지 있으면 추가!
    ],
    entry_points={
        "console_scripts": [
            "whspider = cli:webspider",  # cli.py의 webspider 함수가 진입점!
        ],
    },
)
