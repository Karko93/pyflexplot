#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for module ``pyflexplot.field_specs``."""
import pytest

from dataclasses import dataclass

from pyflexplot.field_specs import FieldSpecs
from pyflexplot.var_specs import MultiVarSpecs

from srutils.testing import is_list_like
from srutils.testing import assert_is_list_like
from srutils.testing import TestConfBase as _TestConf
from srutils.various import isiterable


def check_multi_var_specs_lst(multi_var_specs_lst, len_=None):
    assert_is_list_like(multi_var_specs_lst, len_=len_, children=MultiVarSpecs)


@dataclass(frozen=True)
class Conf_Create(_TestConf):
    name: str
    type_name: str
    vs_dct: dict
    n_vs: int


class Test_Create_Concentration:

    c = Conf_Create(
        name="concentration",
        type_name="FieldSpecs_Concentration",  # SR_TMP
        vs_dct={"nageclass": 0, "numpoint": 0, "time": 1, "integrate": False},
        n_vs=1,
    )

    def test_single_var_specs_one_fld_one_var(self):
        """Single-value-only var specs, for one field, made of one var."""
        var_specs_dct = {
            **self.c.vs_dct,
            "species_id": 1,
            "level": 0,
        }
        multi_var_specs_lst = MultiVarSpecs.create(self.c.name, var_specs_dct)
        check_multi_var_specs_lst(multi_var_specs_lst, len_=self.c.n_vs)
        fld_specs_lst = [
            FieldSpecs(self.c.name, multi_var_specs)
            for multi_var_specs in multi_var_specs_lst
        ]
        assert_is_list_like(fld_specs_lst, len_=self.c.n_vs, children=FieldSpecs)

        fld_specs = next(iter(fld_specs_lst))
        assert fld_specs.name == self.c.name
        assert len(fld_specs.multi_var_specs) == 1

    def test_mult_var_specs_many_flds_one_var_each(self):
        """Multi-value var specs, for multiple fields, made of one var each."""
        var_specs_dct = {
            **self.c.vs_dct,
            "species_id": [1, 2],
            "level": [0, 1],
        }
        multi_var_specs_lst = MultiVarSpecs.create(self.c.name, var_specs_dct)
        check_multi_var_specs_lst(multi_var_specs_lst, len_=4)
        fld_specs_lst = [
            FieldSpecs(self.c.name, multi_var_specs)
            for multi_var_specs in multi_var_specs_lst
        ]
        assert_is_list_like(fld_specs_lst, len_=4, children=FieldSpecs)

        for fld_specs in fld_specs_lst:
            assert fld_specs.name == self.c.name
            assert len(fld_specs.multi_var_specs) == 1

    def test_mult_var_specs_one_fld_many_vars(self):
        """Multi-value var specs, for one field, made of multiple vars."""
        var_specs_dct = {
            **self.c.vs_dct,
            "species_id": (1, 2),
            "level": (0, 1),
        }
        multi_var_specs_lst = MultiVarSpecs.create(self.c.name, var_specs_dct)
        check_multi_var_specs_lst(multi_var_specs_lst, len_=1)
        fld_specs_lst = [
            FieldSpecs(self.c.name, multi_var_specs)
            for multi_var_specs in multi_var_specs_lst
        ]
        assert_is_list_like(fld_specs_lst, len_=1, children=FieldSpecs)

        fld_specs = next(iter(fld_specs_lst))
        assert fld_specs.name == self.c.name
        assert len(fld_specs.multi_var_specs) == 4


class Test_Create_Deposition:

    c = Conf_Create(
        name="deposition",
        type_name="FieldSpecs_Deposition",  # SR_TMP
        vs_dct={
            "nageclass": 0,
            "numpoint": 0,
            "integrate": False,
            "deposition": "tot",
        },
        n_vs=2,
    )

    def test_single_var_specs_one_fld_one_var(self):
        """Single-value-only var specs, for one field, made of one var."""
        var_specs_dct = {
            **self.c.vs_dct,
            "time": 1,
            "species_id": 1,
        }
        multi_var_specs_lst = MultiVarSpecs.create(
            self.c.name, {**var_specs_dct, "deposition": ("wet", "dry")},
        )
        check_multi_var_specs_lst(multi_var_specs_lst, len_=self.c.n_vs)
        fld_specs_lst = [
            FieldSpecs(self.c.name, multi_var_specs)
            for multi_var_specs in multi_var_specs_lst
        ]
        assert_is_list_like(fld_specs_lst, len_=1, children=FieldSpecs)

        fld_specs = next(iter(fld_specs_lst))
        assert fld_specs.name == self.c.name
        assert len(fld_specs.multi_var_specs) == self.c.n_vs

    def test_mult_var_specs_many_flds_one_var_each(self):
        """Multi-value var specs, for multiple fields, made of one var each."""
        vs_dct = {
            **self.c.vs_dct,
            "time": [0, 1, 2],
            "species_id": [1, 2],
        }
        n_vs = self.c.n_vs * 6
        multi_var_specs_lst = MultiVarSpecs.create(self.c.name, vs_dct)
        check_multi_var_specs_lst(multi_var_specs_lst, len_=n_vs)
        fld_specs_lst = [
            FieldSpecs(self.c.name, multi_var_specs)
            for multi_var_specs in multi_var_specs_lst
        ]
        assert_is_list_like(fld_specs_lst, len_=n_vs, children=FieldSpecs)

        for fld_specs in fld_specs_lst:
            assert fld_specs.name == self.c.name
            assert len(fld_specs.multi_var_specs) == self.c.n_vs

    def test_mult_var_specs_one_fld_many_vars(self):
        """Multi-value var specs, for one field, made of multiple vars."""
        vs_dct = {
            **self.c.vs_dct,
            "time": (0, 1, 2),
            "species_id": (1, 2),
        }
        n_vs = self.c.n_vs * 6
        multi_var_specs_lst = MultiVarSpecs.create(self.c.name, vs_dct)
        check_multi_var_specs_lst(multi_var_specs_lst, len_=n_vs)
        fld_specs_lst = [
            FieldSpecs(self.c.name, multi_var_specs)
            for multi_var_specs in multi_var_specs_lst
        ]
        assert_is_list_like(fld_specs_lst, len_=n_vs, children=FieldSpecs)

        fld_specs = next(iter(fld_specs_lst))
        assert fld_specs.name == self.c.name
        assert len(fld_specs.multi_var_specs) == n_vs