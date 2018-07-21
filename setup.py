import setuptools

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="kitten",
    version="0.3.1",
    author="Chris Rehn",
    author_email="chris@rehn.me",
    description="Tiny multi-server automation tool.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hoffa/kitten",
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": {"kitten=kitten:main"}},
    setup_requires=["pytest-runner"],
    tests_require=["pytest"],
    install_requires=["boto3>=1.7", "fabric>=2.2", "six>=1.0"],
    license="MIT",
    classifiers=(
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: System :: Installation/Setup",
        "Topic :: System :: Monitoring",
        "Topic :: System :: Shells",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ),
)
