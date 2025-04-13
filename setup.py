from setuptools import setup, find_packages

setup(
    name="webcrawlerapi-langchain",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "webcrawlerapi==1.0.6",
        "langchain-core>=0.1.0",
    ],
    author="WebCrawlerAPI",
    author_email="support@webcrawlerapi.com",
    description="LangChain integration for WebCrawlerAPI",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/webcrawlerapi/webcrawlerapi-langchain",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 