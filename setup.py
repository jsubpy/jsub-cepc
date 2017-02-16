import os

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(here, 'README.rst')) as f:
    long_description = f.read()

setup(
    name = 'jsub-cepc',
    version = '0.1.0.dev1',
    description = 'JSUB extension for CEPC experiment',
    long_description = long_description,
    url = 'https://jsubpy.github.io/exts/',
    author = 'Xianghu Zhao',
    author_email = 'zhaoxh@ihep.ac.cn',
    license = 'MIT',

    classifiers = [
        'Development Status :: 2 - Pre-Alpha',

        'Intended Audience :: Science/Research',
        'Topic :: System :: Distributed Computing',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],

    keywords = 'jsub extension cepc',
    packages = find_packages(),
    install_requires = [
        'jsub',
    ],
    include_package_data = True,
    tests_require = [
        'pytest',
    ],
)
