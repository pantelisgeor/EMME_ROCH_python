import os
import cdsapi
import os


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
    
    params:
        month: User specified month of the year (1-12)
        year: User specified calendar year
        path_save: Path to directory where downloaded data will be stored
        days: Days of the month (default range(1, 32))
        area: Bounding box for the dataset
        dataset: User specified CDS identifier for the dataset (default: reanalysis-era5-land)
        name_prefix: Prefix identifier for the downloaded dataset filename
        variables: User specified variables to download from CDS
    """

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

    params:
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