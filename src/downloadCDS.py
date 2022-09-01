# ------------------------------------------------------------------------------- #
def downloadCDS(month, year,
                path_save,
                days = range(1, 32),
                area = [43, 18, 33, 36],
                dataset = "reanalysis-era5-land",
                name_prefix = "ERA_land",
                variables = ["2m_dewpoint_temperature", "2m_temperature",
                             "forecast_albedo", "skin_reservoir_content",
                             "surface_sensible_heat_flux", "total_evaporation",
                             "total_precipitation"]):
    """
    Downloads data for a specified month and year from the Copernicus DataStore
    
    Args:
        month: User specified month of the year (1-12)
        year: User specified calendar year
        path_save: Path to directory where downloaded data will be stored
        days: Days of the month (default range(1, 32))
        area: Bounding box for the dataset
        dataset: User specified CDS identifier for the dataset (default: reanalysis-era5-land)
        name_prefix: Prefix identifier for the downloaded dataset filename
        variables: User specified variables to download from CDS
    """

    import os
    import cdsapi

    # Check if the path_save directory exists and create it if not
    if not os.path.isdir(path_save):
        os.mkdir(path_save)
    if not path_save.endswith('/'):
        path_save = f"{path_save}/"

    # If file exists, skip it
    if os.path.isfile(f"{path_save}{name_prefix}_yr_{year}_mnth_{month}.nc"):
        return
    
    # CDS call
    c = cdsapi.Client()

    try:
        c.retrieve(
        dataset,
        {
            'format': 'netcdf',
            'variable': variables,
            'year': str(year),
            'month': str(month),
            'day': [str(x) for x in days],
            'time': [
                '00:00', '01:00', '02:00',
                '03:00', '04:00', '05:00',
                '06:00', '07:00', '08:00',
                '09:00', '10:00', '11:00',
                '12:00', '13:00', '14:00',
                '15:00', '16:00', '17:00',
                '18:00', '19:00', '20:00',
                '21:00', '22:00', '23:00',
            ],
            'area': area,
        },
            f"{path_save}{name_prefix}_yr_{year}_mnth_{month}.nc"
        )
    except Exception as e:
        print("ERROR ERROR ERROR ERROR \n")
        print(e)
        print("\n")


# ------------------------------------------------------------------------------- #
def downloadMultipleCDS(month_start, month_end, year_start, year_end, path_save,
                        days = range(1, 32),
                        area = [43, 18, 33, 36], 
                        dataset = "reanalysis-era5-land",
                        name_prefix = "ERA_land",
                        variables = ["2m_dewpoint_temperature", "2m_temperature",
                                     "forecast_albedo", "skin_reservoir_content",
                                     "surface_sensible_heat_flux", "total_evaporation",
                                     "total_precipitation"]):
    """
    Downloads a range of datasets between month_start/year_start and month_end/year_end

    Args:
        month_start: Calendar month to define the start of the required data time period
        month_end: Calendar month to define the end of the required data time period
        year_start: Year to define the start of the required data time period
        year_end: Year to define the end of the required data time period
        days: Days of the month (default: range(1, 32))
        area: Bounding box for the dataset
        dataset: User specified CDS identifier for the dataset (default: reanalysis-era5-land)
        name_prefix: Prefix identifier for the downloaded dataset filename
        variables: User specified variables to download from CDS
    """

    # Downlaod the data
    if (year_start == year_end):
        for month in range(month_start, month_end + 1):
            downloadCDS(month=month, year=year_start, path_save=path_save,
                        days=days, dataset=dataset, name_prefix=name_prefix,
                        variables=variables, area=area)
    else:
        for year in range(year_start, year_end+1):
            if year == year_start:
                for month in range(month_start, 13):
                    downloadCDS(month=month, year=year, path_save=path_save,
                                days=days, dataset=dataset, name_prefix=name_prefix,
                                variables=variables, area=area)
            elif year == year_end:
                for month in range(1, month_end+1):
                    downloadCDS(month=month, year=year, path_save=path_save,
                                days=days, dataset=dataset, name_prefix=name_prefix,
                                variables=variables, area=area)
            else:
                for month in range(1, 13):
                    downloadCDS(month=month, year=year, path_save=path_save,
                                days=days, dataset=dataset, name_prefix=name_prefix,
                                variables=variables, area=area)


# ------------------------------------------------------------------------------- #
def completeDataset(path_save,
                    diff_threshold = 65,
                    name_prefix = "ERA_land",
                    area = [43, 18, 33, 36],
                    dataset = "reanalysis-era5-land",
                    variables = ["2m_dewpoint_temperature", "2m_temperature",
                                 "forecast_albedo", "skin_reservoir_content",
                                 "surface_sensible_heat_flux", "total_evaporation",
                                 "total_precipitation"]):

    """
    Download missing data and checks for the most up to date data on the CDS dataserver

    Args:
        path_save: Path to directory where downloaded data will be stored
        diff_threshold: Time the defined dataset lags behind current date in days (default: 65)
        name_prefix: Prefix identifier for the downloaded dataset filename
        area: Bounding box for the dataset
        dataset: User specified CDS identifier for the dataset (default: reanalysis-era5-land)
        variables: User specified variables to download from CDS
    """

    import emme_roch as er
    from os import chdir, remove
    from glob import glob
    from pandas import concat
    from warnings import warn
    from datetime import datetime
    from xarray import open_dataset
    from math import floor
    from calendar import monthrange

    # List the contents of the directory
    chdir(path_save)
    files_dir = glob(f"{name_prefix}*.nc")
    files = concat(map(er.climate_temporal.parse_name, files_dir))
    files = files.sort_values(by=['year', 'month'], ascending=True).reset_index(drop=True)
    del files_dir

    files = files.drop(files.index[[2, 17, 18, 19]])  # <---------------------- DELETE THIS

    # Check if the datasets are complete (if there are missing dates between start and end)
    df_data_complete = er.climate_temporal.checkYears(files)
    if df_data_complete is not None:
        df_data_complete.reset_index(drop=True, inplace=True)
        warn("\n\n        WARNING: There are missing dates in the datasets\n \
            ----------- SEE BELOW MISSING DATES -----------\n")
        print(df_data_complete)
        print("\n         ------------------------------------------------")

    # Attempt to download the missing data
    if df_data_complete is not None:
        print("---- Attempting to download missing data ----\n")
        for year in df_data_complete.year.values:
            for month in df_data_complete.loc[df_data_complete.year == year].months_missing.values[0]:
                try:
                    print(f"Downloading: Year: {year} -- Month: {month}")
                    downloadCDS(year=year, month=month,
                                area = area,
                                path_save=path_save,
                                dataset = dataset,
                                name_prefix = name_prefix,
                                variables = variables)
                    print(f"Finished: Year: {year} -- Month: {month}\n")
                except Exception as e:
                    print(f"ERROR:\nYear: {year} -- Month: {month} has failed to download because of: \n{e}")

    # Get the last date in the saved datasets
    # Read the latest netcdf file
    ds = open_dataset(f"{path_save if path_save.endswith('/') else f'{path_save}/'}{files.filename.values[-1]}")
    # Get the last date in the dataset
    last_date = ds.time.values.max()
    last_date = datetime.utcfromtimestamp(last_date.tolist()/1e9)
    # Get the current date
    current_date = datetime.now()
    # Get the time difference between them in days
    time_diff = (current_date - last_date).days
    # Check if the last dataset is complete (ie. all days are present)
    delete_file = False if last_date.day == monthrange(last_date.year, last_date.month)[1] else True

    # If the time_diff is larger that the user defined diff_threshold, download the latest datasets
    if time_diff > diff_threshold:
        # Delete the last dataset if it's not complete
        if delete_file:
            remove(f"{path_save if path_save.endswith('/') else f'{path_save}/'}{files.filename.values[-1]}")
        # Get the details of the deleted file
        year, month = files.loc[files.index[-1]].year, files.loc[files.index[-1]].month
        # If the last file is the same year as the current one, download the data up to two months ago
        if year == current_date.year:
            for mnth in range(month, current_date.month-floor(diff_threshold/30)+1, 1):
                try:
                    print(f"Downloading: Year: {year} -- Month: {mnth}")
                    downloadCDS(year=year, month=mnth,
                                area = area,
                                path_save=path_save,
                                dataset = dataset,
                                name_prefix = name_prefix,
                                variables = variables)
                    print(f"Finished: Year: {year} -- Month: {mnth}\n")
                except Exception as e:
                    print(f"ERROR:\nYear: {year} -- Month: {mnth} has failed to download because of: \n{e}")
        else:
            # Previous year
            for mnth in range(month, 13, 1):
                try:
                    print(f"Downloading: Year: {year} -- Month: {mnth}")
                    downloadCDS(year=year, month=mnth,
                                area = area,
                                path_save=path_save,
                                dataset = dataset,
                                name_prefix = name_prefix,
                                variables = variables)
                    print(f"Finished: Year: {year} -- Month: {mnth}\n")
                except Exception as e:
                    print(f"ERROR:\nYear: {year} -- Month: {mnth} has failed to download because of: \n{e}")
            # Current year
            if current_date.month > 2:
                for mnth in range(1, current_date.month-floor(diff_threshold/30)+1, 1):
                    try:
                        print(f"Downloading: Year: {year} -- Month: {mnth}")
                        downloadCDS(year=current_date.year, month=mnth,
                                    area = area,
                                    path_save=path_save,
                                    dataset = dataset,
                                    name_prefix = name_prefix,
                                    variables = variables)
                        print(f"Finished: Year: {year} -- Month: {mnth}\n")
                    except Exception as e:
                        print(f"ERROR:\nYear: {year} -- Month: {mnth} has failed to download because of: \n{e}")


# ------------------------------------------------------------------------------- #