"""Test the elements of complete plots based on deterministic COSMO-1 data."""
# Local
from .shared import _TestBase
from .shared import _TestCreateReference  # noqa:F401
from .shared import datadir  # noqa:F401  # required by _TestBase.test

INFILE_1 = "flexpart_cosmo-1_2019093012.nc"
INFILE_2 = "flexpart_cosmo-1e-ctrl_2020102105.nc"


# Uncomment to create plots for all tests
# _TestBase = _TestCreatePlot


# Uncomment to references for all tests
# _TestBase = _TestCreateReference


class Test_Concentration(_TestBase):
    reference = "ref_cosmo1_deterministic_concentration"
    setup_dct = {
        "infile": INFILE_1,
        "outfile": f"{reference}.png",
        "model": {
            "name": "COSMO-1",
        },
        "panels": [
            {
                "plot_variable": "concentration",
                "integrate": False,
                "lang": "de",
                "domain": "full",
                "dimensions": {
                    "species_id": 1,
                    "time": 5,
                    "level": 0,
                },
            }
        ],
    }


class Test_IntegratedConcentration(_TestBase):
    reference = "ref_cosmo1_deterministic_integrated_concentration"
    setup_dct = {
        "infile": INFILE_1,
        "outfile": f"{reference}.png",
        "plot_type": "auto",
        "model": {
            "name": "COSMO-1",
        },
        "panels": [
            {
                "plot_variable": "concentration",
                "integrate": True,
                "lang": "en",
                "domain": "ch",
                "dimensions": {
                    "species_id": 1,
                    "time": 10,
                    "level": 0,
                },
            }
        ],
    }


class Test_TotalDeposition(_TestBase):
    reference = "ref_cosmo1_deterministic_total_deposition"
    setup_dct = {
        "infile": INFILE_1,
        "outfile": f"{reference}.png",
        "plot_type": "auto",
        "model": {
            "name": "COSMO-1",
        },
        "panels": [
            {
                "plot_variable": "tot_deposition",
                "integrate": True,
                "lang": "de",
                "domain": "full",
                "dimensions": {
                    "species_id": 1,
                    "time": -1,
                },
            }
        ],
    }


class Test_AffectedArea(_TestBase):
    reference = "ref_cosmo1_deterministic_affected_area"
    setup_dct = {
        "infile": INFILE_1,
        "model": {
            "name": "COSMO-1",
        },
        "outfile": f"{reference}.png",
        "panels": [
            {
                "domain": "ch",
                "plot_variable": "affected_area",
                "integrate": True,
                "lang": "en",
                "dimensions": {
                    "level": 0,
                    "species_id": 1,
                    "time": -1,
                },
            }
        ],
    }


class Test_TotalDeposition_MissingField(_TestBase):
    reference = "ref_cosmo1_deterministic_total_deposition_dummy"
    setup_dct = {
        "infile": INFILE_2,
        "outfile": f"{reference}.png",
        "plot_type": "auto",
        "model": {
            "name": "COSMO-1",
        },
        "panels": [
            {
                "plot_variable": "tot_deposition",
                "integrate": True,
                "lang": "de",
                "domain": "full",
                "dimensions": {
                    "species_id": 1,
                    "time": -1,
                },
            }
        ],
    }


class Test_CloudArrivalTime(_TestBase):
    reference = "ref_cosmo1_deterministic_cloud_arrival_time"
    setup_dct = {
        "infile": INFILE_1,
        "outfile": f"{reference}.png",
        "model": {
            "name": "COSMO-1",
        },
        "panels": [
            {
                "plot_variable": "cloud_arrival_time",
                "integrate": False,
                "lang": "en",
                "domain": "ch",
                "dimensions": {
                    "species_id": 1,
                    "time": 0,
                    "level": 0,
                },
            }
        ],
    }