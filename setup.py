from setuptools import setup
from oslogmerger.oslogmerger import __version__

setup(
    version=__version__,
    setup_requires=['pbr>=2.0.0'],
    pbr=True,
)
