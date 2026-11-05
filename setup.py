from setuptools import find_packages, setup


setup(
    name="replicable-labs",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    entry_points={"console_scripts": ["replicable=replicable_cli.__main__:main"]},
)

