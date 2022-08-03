import numpy as np
import geopandas as gpd
import xarray as xr
from shapely.geometry import Point, Polygon
from shapely.validation import make_valid
import pandas as pd
from tqdm import tqdm
import warnings

# Options
pd.set_option('display.max_columns', 20)
warnings.filterwarnings('ignore')


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
    # print(f"x: {x} \ny: {y}\n")
    # x = round(x, 4)
    # y = round(y, 4)
    # Corners of Polygon
    upper_left = (x+offset, y-offset)
    upper_right = (x+offset, y+offset)
    lower_left = (x-offset, y-offset)
    lower_right = (x-offset, y+offset)
    # Create Polygon shape and return it
    polygon = Polygon([upper_left, upper_right, lower_left, lower_right])
    if not polygon.is_valid:
        polygon = make_valid(polygon)
    return polygon


# ------------------------------------------------------------------------------- # 

path_nc = "/home/pantelis/R/data_EMME_ROCH/climate/ERA_land_yr_2020_mnth_1.nc"
nuts_shp = readNuts(countries=['EL', 'CY'])

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
for lon in tqdm(ds.lon.values):
    for lat in ds.lat.values:
        coords = pd.concat([coords, pd.DataFrame({"lon": [lon], "lat": [lat]})])

coords.reset_index(drop=True, inplace=True)
# Round the numbers
coords = coords.round(1)

# Create a Polygon array based on the x, y positions of the centres and the grid_size
geometries = coords.apply(lambda x: make_polygon(x.lon, x.lat, grid_size), 
                                  axis=1)
coords['geometry'] = geometries
del(geometries)
coords = gpd.GeoDataFrame(coords)

# Set the projection
coords = coords.set_crs(epsg=4326)
# coords['surf_area'] = coords.to_crs(crs=3857).area / 10**6

# Get the surface area of the NUTS admin levels
# nuts_shp['surf_area'] = nuts_shp.area / 10**6


# ------------------------------------------------------------------------------- # 
nuts = nuts_shp.geometry.values[0]

# Percentage overlap of the coords grid cells with a NUTS region

# Get the intersecting members of the coords dataset
coords_inter = coords[coords.intersects(nuts)]
coords_inter.reset_index(drop=True, inplace=True)
# Get the shape of the intersections
coords_inter = coords_inter.assign(surf_area=coords_inter.area,
                                   area_inter=coords_inter.intersection(nuts).area)
# Get the percentage cover and the centroid of the grid boxes
coords_inter = coords_inter.assign(perc_cover=coords_inter.area_inter/coords_inter.surf_area,
                                   lon=coords_inter.centroid.x.round(3),
                                   lat=coords_inter.centroid.y.round(3))
