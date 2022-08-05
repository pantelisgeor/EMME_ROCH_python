import eurostat
import pandas as pd
from datetime import datetime

pd.set_option('display.max_columns', 30)
pd.set_option('display.max_rows', 30)

# ------------------------------------------------------------------------------- #
def weekToDate(date):
    """Convert a yearWweek format date to date (Monday of week)"""
    try:
        r = datetime.strptime(date + '-1', "%YW%W-%w")
    except Exception as e:
        r = None
    return r


# ------------------------------------------------------------------------------- # 
def weeklyEurostat(dataset, path_nc, nuts_shp):
    """
    Downloads a weekly dataset from Eurostat based on the dataset code ID and
    combines it with a weekly climate dataset (Netcdf)

    params:
        dataset: Eurostat dataset identifier
        path_nc: Path to the weekly averaged climate dataset
        nuts_shp: NUTS administrative level shapefile

    returns:
        pandas dataframe with the eurostat and climate variables within
    """

    # Get the NUTS3 averaged dataset
    print('Creating NUTS level area averaged climate dataset. . . \n')
    df_clim = getNutsClimAll(path_nc, nuts_shp, n_jobs=1)

    # Read the eurostat dataset
    print('\nDownloading dataset from Eurostat. . . \n')
    df = eurostat.get_data_df(dataset, flags=False)

    # Subset for the NUTS regions in the climate dataset
    df = df[df['geo\\time'].isin(df_clim.nuts_id.unique())]

    # Melt (wide to long)
    df_long = df.melt(id_vars=['unit', 'age', 'sex', 'geo\\time'], 
                    var_name='Week')

    # Get the date of the Monday of each week
    df_long = df_long.assign(time=df_long.Week.apply(weekToDate))

    # Add the climate variables
    df_ = pd.merge(df_long.rename(columns={'geo\\time': 'nuts_id'}), 
                   df_clim, 
                   on=['nuts_id', 'time'], 
                   how='left')

    return df_


# ------------------------------------------------------------------------------- # 