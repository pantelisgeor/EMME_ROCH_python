from distutils.core import setup
from setuptools import find_packages

setup(name='EMME_ROCH',
      version='1.0',
      description='Data Retrieval and Manipulation tools for EMME ROCH project',
      author='Pantelis Georgiades',
      author_email='p.georgiades@cyi.ac.cy',
      packages=['emme_roch'],
      package_dir={'emme_roch': 'src'},
      python_requires='>=3.7',
      install_requires=['cdsapi', 
                        'geopandas',
                        'shapely<2.0',
                        'xarray',
                        'numpy',
                        'pandas',
                        'tqdm',
                        'eurostat',
                        'netcdf4']
     )