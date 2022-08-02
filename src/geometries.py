from itertools import product
import numpy as np
import geopandas as gpd
import xarray as xr
from shapely.geometry import Point, Polygon
import pandas as pd


# ------------------------------------------------------------------------------- # 
def readNuts(shapefile="data-local/NUTS_RG_20M_2021_4326.shp/NUTS_RG_20M_2021_4326.shp",
             nuts_levels=[3], countries=None):
    """
    Reads the Eurostat NUTS administrative level shapefile and subsets for a user
    specified NUTS level and user specified countries
    
    params:
        shapefile: Path to Eurostat NUTS shapefile
        nuts_levels: User defined NUTS administrative levels list to be returned (default: [3])
        countries: User defined list of countries to be returned (default: None)
    """
    
    # Read the shapefile using the geopandas library
    nuts_shp = gpd.read_file(shapefile)

    # Subset for the specified NUTS level
    nuts_shp = nuts_shp[nuts_shp['LEVL_CODE'].isin(nuts_levels)]

    # Select the specified countries, if such an input was given
    if countries is not None:
        nuts_shp = nuts_shp[nuts_shp['CNTR_CODE'].isin(countries)]

    return nuts_shp


# ------------------------------------------------------------------------------- # 
def make_polygon(x, y, offset):
    """
    Returns a square shapely polygon based on the centre and offset
    
    params:
        x, y: centre point (x, y)
        offset: Side of square / 2
    """
    x = round(x, 2)
    y = round(y, 2)
    # Corners of Polygon
    upper_left = [x+offset, y-offset]
    upper_right = [x+offset, y+offset]
    lower_left = [x-offset, y-offset]
    lower_right = [x-offset, y+offset]
    # Create Polygon shape and return it
    return Polygon([upper_left, upper_right, lower_left, lower_right])


# ------------------------------------------------------------------------------- # 

path_nc = "/home/pantelis/R/data_EMME_ROCH/ERA_land_yr_2020_mnth_12.nc"
# nuts_shp

# Open the netcdf file into an xarray
ds = xr.open_dataset(path_nc)

# Coordinate names
coord_names = ds.coords
for c in coord_names:
    if c in ["longitude", "Longitude", "lon", "Lon", "lons", "Lons"]:
        ds = ds.rename({c: 'lon'})
    elif c in ["latitude", "Latitude", "lat", "Lat", "lats", "Lats"]:
        ds = ds.rename({c: 'lat'})
        

# Get the grid cell size
grid_size = round(abs(ds.lat.values[1] - ds.lat.values[0]) / 2, 3)

# Create a dataframe of the coordinates
coords = pd.DataFrame()
for lon in ds.lon.values:
    coords = pd.concat([coords, pd.DataFrame({"lon": lon, "lat": ds.lat.values})])
# Round the numbers
coords = coords.round(1)
# Create a geopandas geodataframe from the points
coords = gpd.GeoDataFrame(coords, 
                          geometry=gpd.points_from_xy(coords.lon, coords.lat))
# Create a Polygon array based on the x, y positions of the centres and the grid_size
coords['geometry'] = coords.apply(lambda x: make_polygon(x.lon, x.lat, grid_size), axis=1)
# Set the projection
coords = coords.set_crs(epsg=4326)