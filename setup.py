"""Setup script for repomap package."""

import os
from setuptools import setup, find_packages

# Read requirements from file
requirements = []
if os.path.exists('requirements.txt'):
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()

# Read README.md if it exists
readme = 'RepoMap - Code repository mapping tool'
if os.path.exists('README.md'):
    with open('README.md', 'r', encoding='utf-8') as f:
        readme = f.read()

setup(
    name='repomap',
    version='0.1.2',
    packages=find_packages(include=['repomap', 'repomap.*']),
    url='https://github.com/Emasoft/repomap',
    license='Apache-2.0',
    author='Emasoft',
    author_email='713559+Emasoft@users.noreply.github.com',
    description='A tool for mapping and visualizing code repositories',
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    python_requires='>=3.10, <3.14',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Software Development :: Documentation',
    ],
    entry_points={
        'console_scripts': [
            'repomap=repomap:main',
            'ast_parser=repomap.ast_parser:main',
        ],
    },
    scripts=[
        'scripts/repomap.py',
        'scripts/ast_parser.py',
        'repomap.py',
        'ast_parser.py',
    ],
    include_package_data=True,
    package_data={
        'repomap': [
            'queries/*.scm', 
            'queries/tree-sitter-language-pack/*.scm', 
            'queries/tree-sitter-languages/*.scm',
            'queries/fallback/*.scm'
        ],
    },
)
