import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name='twitter_parser',
    version='1.0.0',
    author='Phyllo',
    description='Twitter Parsing Package',
    long_description=long_description,
    long_description_content_type="text/markdown",
    url='https://github.com/getphyllo/phyllo-twitter-parser',
    license='MIT',
    include_package_data=True,
    packages=[
        'twitter_parser/core',
        'twitter_parser/schemas',
        'twitter_parser/utils'
    ],
    install_requires=[
        'httpx>=0.23.0',
        'requests==2.32.0',
        'imagesize>=1.4.0',
        'pydantic==2.11.3'
    ],
)
