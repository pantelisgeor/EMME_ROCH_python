from distutils.core import setup

setup(name='EMME_ROCH',
      version='1.0',
      description='Data Retrieval and Manipulation tools for EMME ROCH project',
      author='Pantelis Georgiades',
      author_email='p.georgiades@cyi.ac.cy',
      packages=['emme_roch'],
      python_requires='>=3.7',
      install_requires=['cdsapi', 
                        'geopandas']
     )