# ------------------------------------------------------------------------------- # 
def parse_name(x):
    """returns the details for the filename"""

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
    
    params:
        files: pandas dataframe with the datasets information

    returns:
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
                df_temp = DataFrame({'year': year, 'months_missing': missing_months})
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
def weekly_cdo(path_dat, name_prefix, path_out=None):
    """
    Uses the system's CDO operations to calculate the weekly mean of a climate
    netcdf variables, starting on a Monday

    params:
        path_dat: Path to where the hourly netcdf files are located
        name_prefix: Prefix str to identify the dataset
        path_out: Directory to save the output dataset (optional)

    returns:
        Nothing - saves the aggregated and weekly averaged netcdfs in the same folder
    """

    import os
    import re
    import datetime
    from glob import glob
    from pandas import concat

    # List the contents of the directory
    os.chdir(path_dat)
    files_dir = glob(f"{name_prefix}*.nc")
    files = concat(map(parse_name, files_dir))
    del files_dir

    # Sort wrt date
    files.sort_values(by=['year', 'month'], ascending=True, inplace=True)
    files.reset_index(drop=True, inplace=True)

    # Check if the datasets are complete (if there are missing dates between start and end)
    df_data_complete = checkYears(files)
    if df_data_complete is not None:
        warnings.warn("\n        WARNING: There are missing dates in the datasets\n \
            ----------- SEE BELOW MISSING DATES -----------\n")
        print(df_data_complete)
        print("\n         ------------------------------------------------")

    # Combine the data
    files_to_join = files[files.temp_res == 'hourly'].filename.values
    files_to_join = [f"{path_dat}/{x}" for x in files_to_join]

    start_date = f"{files.year.min()}{files[files.year == files.year.min()].month.values[0]}"
    end_date = f"{files.year.max()}{files[files.year == files.year.max()].month.values[-1]}"
    out_file = f"{name_prefix}_{start_date}_{end_date}.nc"

    os.system(f"cd {path_dat} && cdo -b F64 -f nc4 -P 4 -O -z zip_5 -s mergetime \
        {' '.join(files[files.temp_res == 'hourly'].filename.values)} \
            {out_file}")

    # Get number of time steps in the file
    steps = os.popen(f"cdo -s -ntime {path_dat}/{out_file}").read()
    steps = int(re.search("[0-9]*", steps).group())

    # Get the start date of the file
    start_date = os.popen(f"cdo -s -infov {path_dat}/{out_file} | head -2").read()
    start_date = re.search("[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}", 
                           start_date).group()

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
    cdo_params = "-O -P 4 -f nc4 -z zip_5 -s"
    os.system(f"cd {path_dat} && \
        time cdo {cdo_params} --timestat_date first -timselmean,{tstep_range} \
        -seltimestep,{tstep_start}/{tstep_end} {out_file} {out_file.replace('.nc', '_weekly.nc')}")

    return


# ------------------------------------------------------------------------------- # 