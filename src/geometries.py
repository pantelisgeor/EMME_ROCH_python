# ------------------------------------------------------------------------------- # 
def readNuts(shapefile="data-local/NUTS_RG_20M_2021_4326.shp/NUTS_RG_20M_2021_4326.shp",
             nuts_levels=[3], countries=None):
    """
    Reads the Eurostat NUTS administrative level shapefile and subsets for a user
    specified NUTS level and user specified countries
    
    Args:
        shapefile: Path to Eurostat NUTS shapefile
        nuts_levels: User defined NUTS administrative levels list to be returned (default: [3])
        countries: User defined list of countries to be returned (default: None)

    Returns:
        nuts_shp: NUTS level shapefile 
    """

    from geopandas import read_file
    
    # Read the shapefile using the geopandas library
    nuts_shp = read_file(shapefile)

    # Subset for the specified NUTS level
    nuts_shp = nuts_shp[nuts_shp['LEVL_CODE'].isin(nuts_levels)]

    # Select the specified countries, if such an input was given
    if countries is not None:
        nuts_shp = nuts_shp[nuts_shp['CNTR_CODE'].isin(countries)]

    return nuts_shp.reset_index(drop=True)


# ------------------------------------------------------------------------------- # 
def make_polygon(x, y, offset):
    """
    Returns a square shapely polygon based on the centre and offset
    
    Args:
        x, y: centre point (x, y)
        offset: Side of square / 2

    Returns:
        polygon: Polygon shape (square)
    """
   
    from shapely.geometry import Polygon
    from shapely.validation import make_valid
   
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
def getNutsclim(nuts_ind, df, nuts_shp, coords):
    """
    Returns the NUTS level area averaged data for a given NUTS region
    
    Args:
        nuts_ind: index of NUTS from the NUTS admin level shapefile
        df: Climate data pandas dataframe
        nuts_shp: NUTS administrative level shapefile (epsg 4326)
        coords: coordinate shapefile from the climate dataset

    Returns:
        pandas dataframe of the NUTS level area averaged climate variables
    """

    from pandas import merge

    # Get the shape of the nuts region
    nuts = nuts_shp.geometry.values[nuts_ind]

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


    df = df.assign(lon=df.lon.round(3), lat=df.lat.round(3))

    # Add the percentage coverage column
    df = merge(df, coords_inter[['lon', 'lat', 'perc_cover']], on=['lon', 'lat'], how='left')
    df.dropna(inplace=True)

    # normalise the percentage coverage for the grid cells in the df dataframe
    grid_points = df.groupby(['lon', 'lat', 'perc_cover'], as_index=False).size().drop('size', axis=1)
    grid_points = grid_points.assign(perc_cover=grid_points.perc_cover/grid_points.perc_cover.sum())
    # Add it back to df
    df = merge(df.drop('perc_cover', axis=1), grid_points, on=['lon', 'lat'], how='left')

    # Normalise the variables
    for var in df.drop(['lon', 'lat', 'time', 'perc_cover'], axis=1).columns:
        df[var] = df[var] * df['perc_cover']

    # Get the area averaged totals
    df_clim = df.drop(['lon', 'lat', 'perc_cover'], axis=1).groupby('time', as_index=False).sum()

    # Add the nuts_id
    df_clim = df_clim.assign(nuts_id=nuts_shp.NUTS_ID.values[nuts_ind])

    return df_clim


# ------------------------------------------------------------------------------- # 
def getNutsClimAll(path_nc, nuts_shp, n_jobs=1):
    """
    Calculates the NUTS area average climage dataset for a given netcdf file

    Args:
        path_nc: path to the netcdf dataset
        nuts_shp: NUTS administrative level shapefile
        n_jobs: Number of parallel processes to open to calculate the NUTS 
                area averaged climate data

    Returns:
        df_clim: pandas dataframe which hold the NUTS level averaged climate data
    """

    import warnings
    from xarray import open_dataset
    from pandas import DataFrame, concat
    from tqdm import tqdm
    from geopandas import GeoDataFrame
    from gc import collect
    from multiprocessing import Pool
    from functools import partial
    from numpy import arange
    warnings.filterwarnings('ignore')

    # Open the netcdf file into an xarray
    ds = open_dataset(path_nc)

    # Coordinate names
    if "time_bnds" in ds.variables:
        ds = ds.drop("time_bnds")
    coord_names = ds.coords
    for c in coord_names:
        if c in ["longitude", "Longitude", "lon", "Lon", "lons", "Lons"]:
            ds = ds.rename({c: 'lon'})
        elif c in ["latitude", "Latitude", "lat", "Lat", "lats", "Lats"]:
            ds = ds.rename({c: 'lat'})

    # Get the grid cell size
    grid_size = round(abs(ds.lat.values[1] - ds.lat.values[0]) / 2, 3)

    # Create a dataframe of the coordinates
    coords = DataFrame()
    for lon in tqdm(ds.lon.values):
        for lat in ds.lat.values:
            coords = concat([coords, DataFrame({"lon": [lon], "lat": [lat]})])

    coords.reset_index(drop=True, inplace=True)
    # Round the numbers
    coords = coords.round(1)

    # Create a Polygon array based on the x, y positions of the centres and the grid_size
    geometries = coords.apply(lambda x: make_polygon(x.lon, x.lat, grid_size), axis=1)
    coords['geometry'] = geometries
    coords = GeoDataFrame(coords)

    # Set the projection
    coords = coords.set_crs(epsg=4326)

    # Convert xarray to pandas dataframe
    df = ds.to_dataframe().reset_index(drop=False)

    # Delete variables that are not needed anymore and run garbage collection
    del ds, coord_names, c, geometries
    collect()

    # Run sequentially or parallel (if n_jobs > 1)
    if n_jobs > 1:
        pool = Pool(n_jobs)
        df_clim = concat(pool.map(partial(getNutsclim, df=df, nuts_shp=nuts_shp,
                                          coords=coords), 
                                  arange(nuts_shp.shape[0])))
        pool.close()
        pool.join()
    else:
        df_clim = DataFrame()
        for ind in tqdm(arange(nuts_shp.shape[0])):
            df_clim = concat([df_clim, getNutsclim(nuts_ind=ind,
                                                   df=df, nuts_shp=nuts_shp,
                                                   coords=coords)])

    return df_clim.reset_index(drop=True)


# ------------------------------------------------------------------------------- # 