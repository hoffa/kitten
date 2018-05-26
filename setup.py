import setuptools

setuptools.setup(
    name="damn",
    version="0.0.1",
    author="Christoffer Rehn",
    author_email="chris@rehn.me",
    packages=setuptools.find_packages(),
    license="MIT",
    install_requires=["boto3", "fabric"],
    scripts=["bin/damn"],
)
