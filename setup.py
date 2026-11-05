from setuptools import find_packages, setup


setup(
    name="replicable-labs",
    version="0.1.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    install_requires=["python-jose[cryptography]>=3.4,<4", "filelock>=3.16,<4"],
    entry_points={"console_scripts": ["replicable=replicable.cli:main"]},
)

