import cdo
import os
from glob import glob
import pandas as pd
import re
import datetime


# ------------------------------------------------------------------------------- # 
def parse_name(x):
    """returns the details for the filename"""
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
        return pd.DataFrame({"year": [year], "month": [month], 
                             "temp_res": [temp_resolution],
                             "filename": [x]})
    except Exception as e:
        print(f"\nERROR: {x} failed to be parsed.\n")


# ------------------------------------------------------------------------------- # 
def weekly_cdo(path_dat, name_prefix):
    """
    Uses the system's CDO operations to calculate the weekly mean of a climate
    netcdf variables, starting on a Monday

    params:
        path_dat: Path to where the hourly netcdf files are located
        name_prefix: Prefix str to identify the dataset

    returns:
        Nothing - saves the aggregated and weekly averaged netcdfs in the same folder
    """

    # List the contents of the directory
    os.chdir(path_dat)
    files_dir = glob(f"{name_prefix}*.nc")
    files = pd.concat(map(parse_name, files_dir))
    del files_dir

    # Sort wrt date
    files.sort_values(by=['year', 'month'], ascending=True, inplace=True)
    files.reset_index(drop=True, inplace=True)

    # Combine the data
    cdo_ = cdo.Cdo()
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
    if first_day != 0:
        day_offset = 7 - first_day
    day_offset = first_day if first_day == 0 else 7-first_day

    # Get the starting time-set (ie. next Monday)
    daily_steps = 24
    tstep_start = 24*day_offset + 1
    tstep_end = steps

    # Weekly means starting on a Monday
    ndays_range = 7
    tstep_range = ndays_range*daily_steps

    # Run the weekly averaging procedure using cdo
    cdo_params = "-O -P 4 -f nc4 -z zip_5 -s"
    os.system(f"cd {path_dat} && \
        time cdo {cdo_params} --timestat_date first -timselmean,{tstep_range} \
        -seltimestep,{tstep_start}/{tstep_end} {out_file} {out_file.replace('.nc', '_weekly.nc')}")

    return


# ------------------------------------------------------------------------------- # 