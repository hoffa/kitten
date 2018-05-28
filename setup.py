import setuptools

with open("README.md") as f:
    long_description = f.read()

setuptools.setup(
    name="kitten",
    version="0.1.8",
    author="Chris Rehn",
    author_email="chris@rehn.me",
    description="Tiny tool to manage multiple servers.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hoffa/kitten",
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": {"kitten=kitten:main"}},
    install_requires=["boto3", "fabric>=2.0"],
    license="MIT",
    classifiers=(
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
    ),
)