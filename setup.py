from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='oslogmerger',

    version='1.0.1',
    description='Openstack Log merge tool',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/mangelajo/oslogmerger',

    # Author details
    author='Miguel Angel Ajo',
    author_email='majopela@redhat.com',

    # Choose your license
    license='Apache Software License',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: Apache Software License',
        'Topic :: Utilities',
        'Environment :: OpenStack',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
    ],

    # What does your project relate to?
    keywords='openstack log merger',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=find_packages(exclude=['contrib', 'docs', 'tests']),

    py_modules=["oslogmerger"],
    # install_requires=['peppercorn'],
    # extras_require={
    #    'dev': ['check-manifest'],
    #    'test': ['coverage'],
    # },
    data_files = ['README.rst'],

    entry_points={
        'console_scripts': [
            'oslogmerger=oslogmerger.oslogmerger:main',
        ],
    },
)

