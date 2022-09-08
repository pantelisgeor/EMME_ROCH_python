# --------------------------------------------------------------------- #
# local imports
# --------------------------------------------------------------------- #

from .climate_temporal import parse_name, weekly_cdo, hourly_to_daily, \
    combine_clim, add_hurs
from .downloadCDS import downloadCDS, downloadMultipleCDS
from .eurostat_data import weekToDate, weeklyEurostat, TLCC
from .geometries import readNuts, make_polygon, \
    getNutsclim, getNutsClimAll

# --------------------------------------------------------------------- #