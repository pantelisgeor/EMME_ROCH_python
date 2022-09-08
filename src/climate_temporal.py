# ------------------------------------------------------------------------------- # 
def parse_name(x):
    """Returns the details for the filename
    
    Args:
        x: string

    Returns:
        Dataframe with parsed name's details
    """

    import re
    from pandas import DataFrame

    try:
        year = re.search("yr_[0-9]*", x)
        year = int(year.group().split('_')[-1])
        month = re.search("mnth_[0-9]*", x)
        month = int(month.group().split('_')[-1])
        if "weekly" in x:
            temp_resolution = "weekly"
        elif "daily" in x:
            temp_resolution = "daily"
        else:
            temp_resolution = "hourly"
        return DataFrame({"year": [year], "month": [month], 
                          "temp_res": [temp_resolution],
                          "filename": [x]})
    except Exception as e:
        print(f"\nERROR: {x} failed to be parsed.\n")


# ------------------------------------------------------------------------------- # 
def checkYears(files):
    """Check if the dataset is complete before joining them.
    
    Args:
        files: pandas dataframe with the datasets information

    Returns:
        pandas dataframe within missing dates if there are any, None otherwise
    """

    from pandas import DataFrame, concat
    
    # Get the min and max year in the files dataframe
    min_year, max_year = files.year.min(), files.year.max()

    # Find the months that are missing from each year
    for year in range(min_year, max_year+1): 
        # List the months in the dataset
        months = files[files.year == year].month.values
        present_months = set(range( 
            files[files.year == year].month.min(), 
            files[files.year == year].month.max() + 1 ))
        # compare the set of the two
        if set(months) != present_months:
            # Get the missing months
            missing_months = list(present_months.difference(set(months)))
            if len(missing_months) > 1:
                df_temp = DataFrame({'year': year, 'months_missing': [missing_months]})
            elif len(missing_months) == 1:
                df_temp = DataFrame({'year': [year], 'months_missing': [missing_months]})
            # Add it to a dataframe to return
            try:
                df_res = concat([df_res, df_temp])
            except NameError:
                df_res = df_temp
            del months, present_months, df_temp, year
    # Return
    try:
        return df_res
    except UnboundLocalError:
        return None


# ------------------------------------------------------------------------------- # 
def checkVariables(path_dat, name_prefix="ERA_land"):
    """
    Loops through the netcdf datasets in a folder and checks if all of them have the 
    same variables so they can be combined.

    Args:
        path_dat: Directory where netcdf datasets are stored
        name_prefix: Dataset identifier

    Returns:
        different: list of datasets with different variables
    """

    import os
    from glob import glob
    from pandas import concat
    from xarray import open_dataset
    from tqdm import tqdm

    # List the contents of the directory
    os.chdir(path_dat)
    files_dir = glob(f"{name_prefix}*.nc")
    files = concat(map(parse_name, files_dir))
    del files_dir
    # Sort wrt date
    files.sort_values(by=['year', 'month'], ascending=True, inplace=True)
    files.reset_index(drop=True, inplace=True)

    # Loop through the datasets and not the unique sets of variables
    variables = []
    different = []
    for f in tqdm(files.filename.values):
        # Read it
        ds = open_dataset(f"{path_dat if path_dat.endswith('/') else f'{path_dat}/'}{f}")
        # List the variables
        vars_temp = [i for i in ds.data_vars]
        if vars_temp not in variables:
            variables.append(vars_temp)
            if f != files.filename.values[0]:
                # print(f"\n--> {f} has a different set of variables\n")
                different.append(f)
        del f, ds, vars_temp

    return different


# ------------------------------------------------------------------------------- # 
def weekly_cdo(path_dat, name_prefix, path_out=None):
    """
    Uses the system's CDO operations to calculate the weekly mean of a climate
    netcdf variables, starting on a Monday

    Args:
        path_dat: Path to where the hourly netcdf files are located
        name_prefix: Prefix str to identify the dataset
        path_out: Directory to save the output dataset (optional)

    Returns:
        Nothing - saves the aggregated and weekly averaged netcdfs in the same folder
    """

    import os
    import re
    import datetime
    from glob import glob
    from pandas import concat
    from warnings import warn

    # List the contents of the directory
    os.chdir(path_dat)
    files_dir = glob(f"{name_prefix}*.nc")
    files = concat(map(parse_name, files_dir))
    del files_dir

    # Sort wrt date
    files.sort_values(by=['year', 'month'], ascending=True, inplace=True)
    files.reset_index(drop=True, inplace=True)

    # Check if all the datasets are the same (ie contain the same variables)
    different_datasets = checkVariables(path_dat=path_dat, name_prefix=name_prefix)
    # If there are any, don't use them below
    if len(different_datasets) > 0:
        files = files.loc[~files.filename.isin(different_datasets)]

    # Check if the datasets are complete (if there are missing dates between start and end)
    df_data_complete = checkYears(files)
    if df_data_complete is not None:
        warn("\n        WARNING: There are missing dates in the datasets\n \
            ----------- SEE BELOW MISSING DATES -----------\n")
        print(df_data_complete)
        print("\n         ------------------------------------------------")


    # Combine the data
    files_to_join = files[files.temp_res == 'hourly'].filename.values
    files_to_join = [f"{path_dat}/{x}" for x in files_to_join]

    start_date = f"{files.year.min()}{files[files.year == files.year.min()].month.values[0]}"
    end_date = f"{files.year.max()}{files[files.year == files.year.max()].month.values[-1]}"
    out_file = f"{name_prefix}_{start_date}_{end_date}.nc"

    if not os.path.isfile(out_file):
        print("Combining datasets. This could take a while. . .\n")
        os.system(f"cd {path_dat} && cdo -b F32 -f nc4 -P 4 -O -z zip_5 -s --verbose mergetime \
            {' '.join(files[files.temp_res == 'hourly'].filename.values)} \
                {out_file}")

    # Get number of time steps in the file
    steps = os.popen(f"cdo -s -ntime {path_dat}/{out_file}").read()
    steps = int(re.search("[0-9]*", steps).group())

    # Get the start date of the file
    start_date = os.popen(f"cdo -s -infov {path_dat}/{out_file} | head -2").read()
    start_date = re.search("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", 
                           start_date).group()
    start_date_string = f"{start_date.split('-')[0]}{int(start_date.split('-')[1])}"

    # Get the name of the first day in the file
    # Starts from Monday (=0)
    first_day = datetime.datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").weekday()
    # If the first day is not a Monday, apply an offset to reach the first Monday
    day_offset = first_day if first_day == 0 else 7 - first_day

    # Get the starting time-set (ie. next Monday)
    daily_steps = 24
    tstep_start = 24*day_offset + 1
    tstep_end = steps

    # Weekly means starting on a Monday
    ndays_range = 7
    tstep_range = ndays_range*daily_steps

    # If the user wants to use a different directory to save the data
    if path_out is not None:
        out_file = f"{path_out}{out_file}" if out_file.endswith('/') else f"{path_out}/{out_file}"

    # Run the weekly averaging procedure using cdo
    cdo_params = "-O -P 8 -f nc4 -z zip_5 -s --verbose"
    if not os.path.isfile(f"{out_file.replace('.nc', '_weekly.nc')}"):
        print('Performing temporal averaging. This could take a while. . .\n')
        os.system(f"cd {path_dat} && \
            time cdo {cdo_params} --timestat_date first -timselmean,{tstep_range} \
            -seltimestep,{tstep_start}/{tstep_end} {name_prefix}_{start_date_string}_{end_date}.nc \
                {out_file.replace('.nc', '_weekly.nc')}")

    return


# ------------------------------------------------------------------------------- # 
def hourly_to_daily(path_hourly, path_daily, name_prefix="ERA_land", 
                    merge_daily=False, path_save_all=None):
    """
    Convert the hourly ERA-land data to daily (temporal interpolations).
    Also calculates the relative humidity and minimum and maximum temperatures for each day

    Args:
        path_hourly: Directory where the hourly ERA5 land dataset is stored
        path_daily: Target directory to save the daily netcdf datasets
        name_prefix: String identifier for the downloaded datasets (default: ERA_land)
        merge_daily: Option to return a single xarray with all the data (all months)
        path_save_all: Path to save the combined dataset (default: None). If nothing is set, 
                       it won't save it

    Returns:
        ds: Combined xarray of all the months processed (boolean, default=False)
    """
    
    # imports
    import os
    from glob import glob
    from warnings import warn

    from numpy import exp
    from pandas import concat
    from tqdm import tqdm
    from xarray import open_dataset

    # Check if the path_daily (target directory) exists
    if not os.path.isdir(path_daily):
        os.mkdir(path_daily)

    # List the contents of the directory (hourly datasets)
    os.chdir(path_hourly)
    files_dir = glob(f"{name_prefix}*.nc")
    files = concat(map(parse_name, files_dir))
    del files_dir

    # Sort wrt date
    files.sort_values(by=['year', 'month'], ascending=True, inplace=True)
    files.reset_index(drop=True, inplace=True)

    # Check if all the datasets are the same (ie contain the same variables)
    different_datasets = checkVariables(path_dat=path_hourly, name_prefix=name_prefix)
    # If there are any, don't use them below
    if len(different_datasets) > 0:
        files = files.loc[~files.filename.isin(different_datasets)]

    # Check if the datasets are complete (if there are missing dates between start and end)
    df_data_complete = checkYears(files)
    if df_data_complete is not None:
        warn("\n        WARNING: There are missing dates in the datasets\n \
            ----------- SEE BELOW MISSING DATES -----------\n")
        print(df_data_complete)
        print("\n         ------------------------------------------------")


    # Loop through the hourly datasets, convert them to daily averages and save them in the
    # path_daily directory with the same filename
    for f in tqdm(files.filename.values):

        # Check if the dataset is already present in the directory and skip it if it does
        if os.path.isfile(f"{path_daily if path_daily.endswith('/') else f'{path_daily}/'}{f}"):
            continue
        
        # Read the file
        ds = open_dataset(f"{path_hourly if path_hourly.endswith('/') else f'{path_hourly}/'}{f}")
        
        # Relative Humidity
        if 'hurs' not in ds.variables:
            # Calculate the relative humidity variable
            # https://www.omnicalculator.com/physics/relative-humidity
            RH = 100 * (exp( ( 17.625 * (ds["d2m"]-273.15) ) / ( 243.04 + (ds["d2m"]-273.15) ) ) / \
                exp( ( 17.625 * (ds["t2m"]-273.15) ) / ( 243.04 + (ds["t2m"] - 273.15) ) ))
            RH.name = "hurs"
            RH.attrs = dict(description="Relative Humidity", units="%")
            # Add it to the ds netcdf
            ds = ds.merge(RH)
        
        # Calculate the daily averages of the variables in the dataset
        # Drop total precipitation, as this is calculated as the total, not mean
        ds_daily = ds.drop("tp").resample(time="D").mean()
        # Add the total precipitation
        ds_daily = ds_daily.merge(ds["tp"].resample(time="D").sum())
        # Also add the minimum and maximum daily temperatures
        ds_daily = ds_daily.merge(ds["t2m"].resample(time="D").min().rename("t2m_min"))
        ds_daily = ds_daily.merge(ds["t2m"].resample(time="D").max().rename("t2m_max"))
        
        # Save it in the path_daily directory
        ds_daily.to_netcdf(f"{path_daily if path_daily.endswith('/') else f'{path_daily}/'}{f}")

    if merge_daily:
        for f in tqdm(files.filename.values):
            # If it's the first set it as ds to merge the rest on it
            if f == files.filename.values[0]:
                ds = open_dataset(f"{path_daily if path_daily.endswith('/') else f'{path_daily}/'}{f}")
            else:
                # Read the next one and merge with the previous combined ones
                ds = ds.merge(open_dataset(f"{path_daily if path_daily.endswith('/') else f'{path_daily}/'}{f}"))
            # Save it to the user defined path as netcdf (if the user has set one, otherwise skip)
            if path_save_all is not None:
                ds.to_netcdf(path_save_all)
        return ds


# ------------------------------------------------------------------------------- # 
def combine_clim(path_dat, name_prefix, mon_start, mon_end, year_start, year_end):
    """
    Return an xarray which contains the data between the start and end user defined dates
    from a directory (path_dat)

    Args:
        path_dat: Directory where datasets are stored
        name_prefix: Dataset identifier
        mon_start: Month to start the dataset
        mon_end: Month to end the dataset
        year_start: Year to start tne dataset
        year_end: Year to end the dataset

    Returns:
        ds: Combined climated dataset for the user specified time period
    """

    # imports
    import os
    from glob import glob
    from warnings import warn

    from pandas import concat
    from tqdm import tqdm
    from xarray import open_dataset

    # Check if path_dat ends with the / character and add it if not
    path_dat = path_dat if path_dat.endswith("/") else f"{path_dat}/"

    # List the contents of the directory (hourly datasets)
    os.chdir(path_dat)
    files_dir = glob(f"{name_prefix}*.nc")
    files = concat(map(parse_name, files_dir))
    del files_dir

    # Sort wrt date
    files.sort_values(by=['year', 'month'], ascending=True, inplace=True)
    files.reset_index(drop=True, inplace=True)

    # Subset based on the year start
    files = files.loc[files.year >= year_start]

    # Check if all the datasets are the same (ie contain the same variables)
    different_datasets = checkVariables(path_dat=path_dat, name_prefix=name_prefix)
    # If there are any, don't use them below
    if len(different_datasets) > 0:
        files = files.loc[~files.filename.isin(different_datasets)]

    # Check if the datasets are complete (if there are missing dates between start and end)
    df_data_complete = checkYears(files)
    if df_data_complete is not None:
        warn("\n        WARNING: There are missing dates in the datasets\n \
            ----------- SEE BELOW MISSING DATES -----------\n")
        print(df_data_complete)
        print("\n         ------------------------------------------------")

    # Loop through the dates, read the dataset and combine them
    for year in tqdm(range(year_start, year_end+1)):
        if year == year_start:
            for month in range(mon_start, 13):
                try:
                    ds_ = open_dataset(
                        f"{path_dat}{files.loc[(files.month == month) & (files.year == year)].filename.values[0]}")
                    try:
                        ds = ds.merge(ds_)
                    except Exception as e:
                        ds = ds_
                    del ds_
                except Exception as e:
                    print(f"Year: {year} -- Month: {month} has failed because of \n{e}")
        elif year == year_end:
            for month in range(1, mon_end+1):
                try:
                    ds_ = open_dataset(
                        f"{path_dat}{files.loc[(files.month == month) & (files.year == year)].filename.values[0]}")
                    try:
                        ds = ds.merge(ds_)
                    except Exception as e:
                        ds = ds_
                    del ds_
                except Exception as e:
                    print(f"Year: {year} -- Month: {month} has failed because of \n{e}")
        else:
            for month in range(1, 13):
                try:
                    ds_ = open_dataset(
                        f"{path_dat}{files.loc[(files.month == month) & (files.year == year)].filename.values[0]}")
                    try:
                        ds = ds.merge(ds_)
                    except Exception as e:
                        ds = ds_
                    del ds_
                except Exception as e:
                    print(f"Year: {year} -- Month: {month} has failed because of \n{e}")

    return ds


# ------------------------------------------------------------------------------- # 
def add_hurs(path_in, path_out, name_prefix="ERA_land"):
    """
    Adds the Relative Humidity variable in the netcdf dataset and saves it elsewhere

    Args:
        path_in: Directory which holds the netcdf datasets without hurs
        path_out: Directory to save the datasets with the hurs variable
        name_prefix: Dataset identifier (default: "ERA_land" )
    """

    # imports
    import os
    from glob import glob
    from warnings import warn

    from pandas import concat
    from numpy import exp
    from tqdm import tqdm
    from xarray import open_dataset

    # Check if paths end with the / character and add it if not
    path_in = path_in if path_in.endswith("/") else f"{path_in}/"
    path_out = path_out if path_out.endswith("/") else f"{path_out}/"

    # Check if the path_out directory exists and create it if not
    if not os.path.isdir(path_out):
        os.mkdir(path_out)

    # List the contents of the directory (hourly datasets)
    os.chdir(path_in)
    files_dir = glob(f"{name_prefix}*.nc")
    files = concat(map(parse_name, files_dir))
    del files_dir

    # Sort wrt date
    files.sort_values(by=['year', 'month'], ascending=True, inplace=True)
    files.reset_index(drop=True, inplace=True)

    # Check if all the datasets are the same (ie contain the same variables)
    different_datasets = checkVariables(path_dat=path_in, name_prefix=name_prefix)
    # If there are any, don't use them below
    if len(different_datasets) > 0:
        files = files.loc[~files.filename.isin(different_datasets)]

    # Check if the datasets are complete (if there are missing dates between start and end)
    df_data_complete = checkYears(files)
    if df_data_complete is not None:
        warn("\n        WARNING: There are missing dates in the datasets\n \
            ----------- SEE BELOW MISSING DATES -----------\n")
        print(df_data_complete)
        print("\n         ------------------------------------------------")


    # Loop through the datasets in files and add the hurs variable and save 
    # them in the path_out directory
    for f in tqdm(files.filename.values):
        # Check if the dataset is already present in the directory and skip it if it does
        if os.path.isfile(f"{path_out}{f}"):
            continue
        # Read the dataset
        ds = open_dataset(f"{path_in}{f}")
        # Calculate the relative humidity variable
        # https://www.omnicalculator.com/physics/relative-humidity
        RH = 100 * (exp( ( 17.625 * (ds["d2m"]-273.15) ) / ( 243.04 + (ds["d2m"]-273.15) ) ) / \
            exp( ( 17.625 * (ds["t2m"]-273.15) ) / ( 243.04 + (ds["t2m"] - 273.15) ) ))
        RH.name = "hurs"
        RH.attrs = dict(description="Relative Humidity", units="%")
        # Add it to the ds netcdf
        ds = ds.merge(RH)
        # Save it
        ds.to_netcdf(f"{path_out}{f}")


# ------------------------------------------------------------------------------- # 