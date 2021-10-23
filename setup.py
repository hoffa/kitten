import setuptools

with open("README.rst") as f:
    long_description = f.read()

setuptools.setup(
    name="kitten",
    version="0.6.2",
    author="Chris Rehn",
    author_email="chris@rehn.me",
    description="Tiny multi-server automation tool.",
    long_description=long_description,
    url="https://github.com/hoffa/kitten",
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": {"kitten=kitten:main"}},
    install_requires=["boto3", "fabric>=2.4"],
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    license="MIT",
    classifiers=(
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ),
    python_requires=">=3.6",
)
