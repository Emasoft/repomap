from setuptools import setup, find_packages
import os

# Read requirements from file
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Read README.md if it exists
readme = 'RepoMap - Code repository mapping tool'
if os.path.exists('README.md'):
    with open('README.md', 'r') as f:
        readme = f.read()

setup(
    name='RepoMap',
    version='0.1.0',
    packages=find_packages(),
    url='https://github.com/emanuelesabetta/RepoMap',
    license='MIT',
    author='emanuelesabetta',
    author_email='',
    description='A tool for mapping and visualizing code repositories',
    long_description=readme,
    long_description_content_type='text/markdown',
    install_requires=requirements,
    python_requires='>=3.8',
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    entry_points={
        'console_scripts': [
            'repomap=repomap.__main__:main',
        ],
    },
)
