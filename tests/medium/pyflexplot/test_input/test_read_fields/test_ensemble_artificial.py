"""Tests for module ``pyflexplot.input.read_fields``.

These tests use artificial ensemble data comprised of input fields that are
constant and equal in value to the respective ensemble member id.

"""
# Standard library
from dataclasses import dataclass
from typing import List

# Third-party
import numpy as np
import pytest  # type: ignore

# First-party
from pyflexplot.input.read_fields import FieldInputOrganizer
from pyflexplot.setup import SetupCollection

# Local  isort:skip
from ..shared import datadir_artificial as datadir  # noqa:F401 isort:skip


@dataclass
class Config:
    ens_mem_ids: List[int]
    ens_var: str


@pytest.mark.parametrize(
    "config",
    [
        Config(ens_mem_ids=[0], ens_var="mean"),  # config[0]
        Config(ens_mem_ids=[1], ens_var="mean"),  # config[1]
        Config(ens_mem_ids=[0, 10], ens_var="minimum"),  # [conf2]
        Config(ens_mem_ids=[0, 10], ens_var="mean"),  # [conf3]
        Config(ens_mem_ids=[0, 10], ens_var="median"),  # config[4]
        Config(ens_mem_ids=[0, 10], ens_var="maximum"),  # [conf5]
        Config(ens_mem_ids=[2, 4, 8, 16], ens_var="minimum"),  # [conf6]
        Config(ens_mem_ids=[2, 4, 8, 16], ens_var="mean"),  # [conf7]
        Config(ens_mem_ids=[2, 4, 8, 16], ens_var="median"),  # conf8]
        Config(ens_mem_ids=[2, 4, 8, 16], ens_var="maximum"),  # [conf9]
    ],
)
def test_one_setup_one_field(datadir, config):  # noqa:F811
    datafile_fmt = f"{datadir}/flexpart_cosmo-2e_const_{{ens_member:03d}}.nc"

    reader = FieldInputOrganizer(datafile_fmt)

    setup_dct = {
        "infile": "foo.nc",
        "outfile": "bar.png",
        "model": "COSMO-2E",
        "input_variable": "concentration",
        "ens_member_id": config.ens_mem_ids,
        "dimensions": {"time": -1, "species_id": 1, "level": 0},
        "ens_variable": config.ens_var,
    }
    setup_dct_lst = [setup_dct]
    setups = SetupCollection.create(setup_dct_lst)
    field_lst_lst = reader.run(setups)

    assert len(field_lst_lst) == 1
    field_lst = next(iter(field_lst_lst))
    assert len(field_lst) == 1
    field = next(iter(field_lst))
    fld = field.fld

    assert np.allclose([fld.min(), fld.max()], fld.mean())

    f_reduce = {
        "minimum": np.min,
        "maximum": np.max,
        "mean": np.mean,
        "median": np.median,
    }[config.ens_var]

    res = f_reduce(fld)
    sol = f_reduce(config.ens_mem_ids)
    assert np.isclose(res, sol)