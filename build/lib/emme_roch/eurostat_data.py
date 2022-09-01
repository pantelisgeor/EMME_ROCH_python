# ------------------------------------------------------------------------------- #
def weekToDate(date):
    """Convert a yearWweek format date to date (Monday of week)"""

    from datetime import datetime

    try:
        r = datetime.strptime(date + '-1', "%YW%W-%w")
    except Exception as e:
        r = None
    return r


# ------------------------------------------------------------------------------- # 
def weeklyEurostat(dataset, path_nc, nuts_shp, n_jobs=1):
    """
    Downloads a weekly dataset from Eurostat based on the dataset code ID and
    combines it with a weekly climate dataset (Netcdf)

    params:
        dataset: Eurostat dataset identifier
        path_nc: Path to the weekly averaged climate dataset
        nuts_shp: NUTS administrative level shapefile
        n_jobs: Number of processes to calculate the climate spatial averaged data

    returns:
        pandas dataframe with the eurostat and climate variables within
    """

    import eurostat
    from pandas import merge
    # Local import
    from emme_roch import getNutsClimAll

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
    df_ = merge(df_long.rename(columns={'geo\\time': 'nuts_id'}), 
                df_clim, 
                on=['nuts_id', 'time'], 
                how='left')

    return df_


# ------------------------------------------------------------------------------- # 
def TLCC(df, nuts_id, age_group="TOTAL", start=-30, end=30, plot=False, plot_corrs=False):

    """
    Calculates the Time Lagged Cross correlation of the input variable wrt to a set of climatic variables

    params:
        df: Pandas dataframe which contains both the values of the variable 
            to investigate and the climatic variables
        nuts_id: NUTS3 ID to perform the TLCC analysis
        age_group: Age group to investigate
        start: Lag times window start
        end: Lag times window end
        plot: Plot the time-series of the input variable
        plot_corrs: Plot the TLCC graphs for all the climatic variables

    returns:
        lagged_correlations: TLCC matrix (pandas dataframe)
    """

    import seaborn as sns
    from pandas import DataFrame, to_datetime
    from matplotlib import pyplot as plt

    # Select data for the specified NUTS ID and age group
    df_ = df.loc[(df.nuts_id == nuts_id) & (df.age == age_group)]
    # Convert time to datetime objects
    df_ = df_.assign(time=to_datetime(df_.time.values))
    # Drop missing values
    df_ = df_.dropna().reset_index(drop=True)

    if plot:
        # Plot the Female and Male statistics
        fig, ax = plt.subplots(1, 1, figsize=(20, 10))
        sns.lineplot(x=df_.loc[df_.sex == 'F'].time, y=df_.loc[df_.sex == 'F'].value, ax=ax, label='Female')
        sns.lineplot(x=df_.loc[df_.sex == 'M'].time, y=df_.loc[df_.sex == 'M'].value, ax=ax, label='Male')
        ax.set(xlabel='Time', ylabel='Deaths per week')
        plt.show()

        return

    # List the climate variables
    list_clim = df_.drop(['unit', 'age', 'sex', 'nuts_id', 'Week', 'value', 'time'], axis=1).columns

    # Calculate the time lagged cross correlations
    lagged_correlation = DataFrame.from_dict(
        {x: [df_[x].corr(df_['value'].shift(-t)) for t in range(start, end)] for x in list_clim})

    # Add the lag time column
    lagged_correlation = lagged_correlation.assign(lag_time=range(start, end))

    if plot_corrs:
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        sns.set(font_scale=2)
        sns.set_style('darkgrid')
        for feat in list_clim:
            sns.lineplot(x=lagged_correlation.lag_time, y=lagged_correlation[feat],
                        ax=ax, label=feat, linewidth=2)
        ax.set(xlabel='Lag Time', ylabel='Time Lagged Cross Correlation', title=nuts_id)
        ax.legend(loc="upper right", frameon=False)
        plt.tight_layout()
        plt.show()
    else:
        return lagged_correlation