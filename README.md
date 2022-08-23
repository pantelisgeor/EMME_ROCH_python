# EMME-ROCH project

Python code-base for the EMME-ROCH project, which downloads climate data from the Copernicus DataStore and Eurostat data.

## Installation

Clone the github repository `https://github.com/pantelisgeor/EMME_ROCH_python`, navigate to folder and install using the setup.py script.

```bash
git clone https://github.com/pantelisgeor/EMME_ROCH_python
cd EMME_ROCH_python
python setup.py install
```

**NOTE** The CDO operator is required for the spatial manipulation of gridded climate datasets. It can be installed through conda or `https://code.mpimet.mpg.de/projects/cdo/files`.

## Usage

### Downloading climate datasets

By default the EMME-ROCH downloads the ERA5-land dataset (`https://confluence.ecmwf.int/display/CKB/ERA5-Land%3A+data+documentation`) from the Copernicus DataStore for the EMME region (Eastern Meditteranean and Middle East) in monthly chunks.

To be able to retrieve datasets from the Copernicus DataStore (CDS), a valid user account is needed, which can be obtained free of charge from `https://cds.climate.copernicus.eu`.

The **downloadCDS()** function can be used to download a specified dataset from CDS for a specified month and year to a user specified directory (path_save) as follows:

```python
import emme_roch as er

er.downloadCDS(month, 
               year,
               path_save,
               days = range(1, 32),
               area = [43, 18, 33, 36],
               dataset = "reanalysis-era5-land",
               name_prefix = "ERA_land",
               variables = ["2m_dewpoint_temperature", "2m_temperature",
                            "forecast_albedo", "skin_reservoir_content",
                            "surface_sensible_heat_flux", "total_evaporation",
                            "total_precipitation"])
```

The days, area, dataset, name_prefix and variables arguments presented above are the default arguments and can be altered by the user to meet other needs. The name_prefix argument is used to construct the filename of the downloaded dataset, which is of the form **[name_prefix]\_yr_[year]\_mnth_[month].nc**.

In addition, the user can download all the data for a specified time period (determined by the start year/month and end year/month), to a specified directory (path_save), as in the following code block. Similarly to the previous example, the days, area, dataset, name_prefix and variables arguments used here are the defaults used in the package and can be ommitted.

```python
import emme_roch as er

er.downloadMultipleCDS(month_start, month_end, 
                       year_start, year_end, 
                       path_save,
                       days = range(1, 32),
                       area = [43, 18, 33, 36], 
                       dataset = "reanalysis-era5-land",
                       name_prefix = "ERA_land",
                       variables = ["2m_dewpoint_temperature", "2m_temperature",
                                    "forecast_albedo", "skin_reservoir_content",
                                    "surface_sensible_heat_flux", "total_evaporation",
                                    "total_precipitation"])
```

To keep the data up to date, the user can periodically use the ***completeDataset()*** function. Make sure to use the same parameters (area, dataset, name_prefix, variables) as the already downloaded datasets. The function checks the latest dataset present in the path_save directory, if incomplete (ie. there are missing days) it downloads it again to get the most recent version and completes the data up to the most recently available for the specified dataset. The *diff_threshold* parameter specifies the lag time of the dataset with respect to the current date in days (for the ERA5-land dataset is 2-3 months, so the default value here is 65 days).

```python
import emme_roch as er

er.completeDataset(path_save,
                   diff_threshold = 65,
                   name_prefix = "ERA_land",
                   area = [43, 18, 33, 36],
                   dataset = "reanalysis-era5-land",
                   variables = ["2m_dewpoint_temperature", "2m_temperature",
                                "forecast_albedo", "skin_reservoir_content",
                                "surface_sensible_heat_flux", "total_evaporation",
                                "total_precipitation"])
```

## Spatial and temporal averaging of climate data

Using the ***weekly_cdo()*** function, the user can combine multiple monthly datasets (with an hourly temporal resolution) and calculate the weekly average of the variables in the datasets (weekly temporal resolution starting on the first Monday of the combined dataset).

```python
import emme_roch as er

weekly_cdo(path_dat, name_prefix, path_out=None)
```

The *path_dat* variable defines the directory where the hourly netcdf datasets are stored and the *name_prefix* is the dataset identifier (eg. ERA_land for the default ERA5-land dataset used in this package). The function uses the system's CDO installation to combine the hourly datasets into a large netcdf containing all the datasets in the path_dat directory and then calculates the weekly averages (starting on the first Monday of the dataset) and the stores it in the same directory, unless the user defines the *path_out* variable, which is None by default.

In addition to the temporal averaging of the data, spatial avereges can also be performed to obtain area averaged on an administrative level, in this example the NUTS3 administrative level for Cyprus and Greece. The package requires the shapefile of the administrative level, which for this example was obtained through Eurostat (`https://ec.europa.eu/eurostat/web/gisco/geodata/reference-data/administrative-units-statistical-units/nuts`).

***NOTE:*** The EPSG:4326 coordinate reference system and the shapefile (SHP) format are required.  

```python
import emme_roch as er

# Read the NUTS3 administrative level shapefile (saved in data-local directory)
# nuts_level defines the admin level (NUTS3 in this case) and countries the countries for which
# to subset the shapefile for (in this example Cyprus and Greece)
nuts3 = er.readNuts(shapefile="data-local/NUTS_RG_20M_2021_4326.shp/NUTS_RG_20M_2021_4326.shp",
                    nuts_levels=[3], countries=["CY", "EL"])

# Create the weekly average of the downloaded netcdfs in a directory
er.weekly_cdo(path_dat="../data/", name_prefix="ERA_land", path_out="../weekly")

# Perform the NUTS3 admin level spatial averages
# Setting n_jobs=1 will calculate the spatial average for each NUTS3 level in the shapefile
# sequentially, whereas n_jobs>1 will use the multiprocessing module to perform parallel 
# operations. 
# NOTE: Parallel calculation is memory heavy
# NOTE: This step is performed in the weeklyEurostat function, there's no need to run it separately
df =  er.getNutsClimAll(path_nc="../weekly/ERA_land_20001_20225_weekly.nc", 
                        nuts_shp=nuts3, n_jobs=8)

# Eurostat data
# The Deaths by week, sex, 5-year age group and NUTS3 region (demo_r_mweek3) dataset 
# will be used as an example
df_weeklydeaths = er.weeklyEurostat(dataset="demo_r_mweek3", 
                                    path_nc="../weekly/ERA_land_20001_20225_weekly.nc",
                                    nuts_shp=nuts3)
```
