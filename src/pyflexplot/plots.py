# -*- coding: utf-8 -*-
"""
Plot types.
"""
# Standard library
import warnings
from datetime import datetime
from textwrap import dedent
from typing import Any
from typing import Collection
from typing import Dict
from typing import Iterator
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

# Third-party
import matplotlib as mpl
import numpy as np

# First-party
from srutils.geo import Degrees

# Local
from .boxed_plot import BoxedPlot
from .boxed_plot import BoxedPlotConfig
from .data import Field
from .data import FieldAllNaNError
from .formatting import format_level_ranges
from .formatting import format_range
from .meta_data import MetaData
from .meta_data import format_unit
from .meta_data import get_integr_type
from .plot_elements import MapAxesConf
from .plot_elements import TextBoxAxes
from .setup import FilePathFormatter
from .setup import InputSetup
from .setup import InputSetupCollection
from .typing import ColorType
from .words import SYMBOLS
from .words import WORDS
from .words import TranslatedWords
from .words import Words


def create_map_conf(field: Field) -> MapAxesConf:
    domain = field.var_setups.collect_equal("domain")
    model = field.nc_meta_data["analysis"]["model"]

    conf_base: Dict[str, Any] = {"lang": field.var_setups.collect_equal("lang")}

    conf_model_ifs: Dict[str, Any] = {"geo_res": "50m"}
    conf_model_cosmo: Dict[str, Any] = {"geo_res": "10m"}

    # SR_TMP < TODO generalize based on meta data
    conf_domain_japan: Dict[str, Any] = {
        "geo_res_cities": "50m",
        "geo_res_rivers": "50m",
        "min_city_pop": 4_000_000,
        "lllat": 20,
        "urlat": 50,
        "lllon": 110,
        "urlon": 160,
        "ref_dist_conf": {"dist": 500},
    }
    # SR_TMP >
    conf_scale_continent: Dict[str, Any] = {
        "geo_res_cities": "50m",
        "geo_res_rivers": "50m",
        "min_city_pop": 300_000,
    }
    conf_scale_country: Dict[str, Any] = {
        "geo_res_cities": "10m",
        "geo_res_rivers": "10m",
        "min_city_pop": 0,
        "ref_dist_conf": {"dist": 25},
    }

    conf: Dict[str, Any]
    if (model, domain) in [("cosmo1", "auto"), ("cosmo2", "auto")]:
        conf = {
            **conf_base,
            **conf_model_cosmo,
            **conf_scale_continent,
            "zoom_fact": 1.05,
        }
    elif (model, domain) == ("cosmo1", "ch"):
        conf = {
            **conf_base,
            **conf_model_cosmo,
            **conf_scale_country,
            "zoom_fact": 3.6,
            "rel_offset": (-0.02, 0.045),
        }
    elif (model, domain) == ("cosmo2", "ch"):
        conf = {
            **conf_base,
            **conf_model_cosmo,
            **conf_scale_country,
            "zoom_fact": 3.23,
            "rel_offset": (0.037, 0.1065),
        }
    elif (model, domain) == ("ifs", "auto"):
        # SR_TMP < TODO Generalize IFS domains
        conf = {**conf_base, **conf_model_ifs, **conf_domain_japan}
        # SR_TMP >
    else:
        raise Exception(f"unknown domain '{domain}' for model '{model}'")

    return MapAxesConf(**conf)


def capitalize(s: str) -> str:
    """Capitalize the first letter while leaving all others as they are."""
    if not s:
        return s
    try:
        return s[0].upper() + s[1:]
    except Exception:
        raise ValueError("s not capitalizable", s)


# SR_TODO Create dataclass with default values for text box setup
# pylint: disable=R0912  # too-many-branches
# pylint: disable=R0914  # too-many-locals
# pylint: disable=R0915  # too-many-statements
def create_plot_config(
    setup: InputSetup, words: TranslatedWords, symbols: Words, mdata: MetaData,
) -> BoxedPlotConfig:
    words.set_active_lang(setup.lang)
    new_config_dct: Dict[str, Any] = {
        "setup": setup,
        "mdata": mdata,
        "labels": {},
    }
    new_config_dct["labels"]["top"] = {
        "tl": "",  # SR_TMP force into 1st position of dict (for tests)
        "bl": (
            f"{format_integr_period(mdata, setup, words, cap=True)}"
            f" {words['since']}"
            f" +{mdata.simulation_integr_start_rel}"
        ),
        "tr": (f"{mdata.simulation_now} (+{mdata.simulation_now_rel})"),
        "br": (
            f"{mdata.simulation_now_rel} {words['since']}"
            f" {words['release_start']}"
            # f" {words['at', 'place']} {mdata.release_site_name}"
        ),
    }
    new_config_dct["labels"]["right_top"] = {
        "title": f"{words['data'].c}",
        "lines": [],
    }
    new_config_dct["labels"]["right_middle"] = {
        "title": "",  # SR_TMP Force into 1st position in dict (for tests)
        "title_unit": "",  # SR_TMP Force into 2nd position in dict (for tests)
        "release_site": words["release_site"].s,
        "site": words["site"].s,
        "max": words["maximum", "abbr"].s,
        "maximum": words["maximum"].s,
    }
    new_config_dct["labels"]["right_bottom"] = {
        "title": words["release"].t,
        "start": words["start"].s,
        "end": words["end"].s,
        "latitude": words["latitude"].s,
        "longitude": words["longitude"].s,
        "lat_deg_fmt": format_coord_label("north", words, symbols),
        "lon_deg_fmt": format_coord_label("east", words, symbols),
        "height": words["height"].s,
        "rate": words["rate"].s,
        "mass": words["total_mass"].s,
        "site": words["site"].s,
        "release_site": words["release_site"].s,
        "max": words["maximum", "abbr"].s,
        "name": words["substance"].s,
        "half_life": words["half_life"].s,
        "deposit_vel": words["deposition_velocity", "abbr"].s,
        "sediment_vel": words["sedimentation_velocity", "abbr"].s,
        "washout_coeff": words["washout_coeff"].s,
        "washout_exponent": words["washout_exponent"].s,
    }
    _info_fmt_base = (
        f"{words['flexpart']} {words['based_on']}"
        f" {mdata.simulation_model_name}{{ens}},"
        f" {mdata.simulation_start}"
    )
    new_config_dct["labels"]["bottom"] = {
        "model_info_det": _info_fmt_base.format(ens=""),
        "model_info_ens": _info_fmt_base.format(
            ens=(
                f" {words['ensemble']}"
                f" ({len(setup.ens_member_id or [])} {words['member', 'pl']}:"
                f" {format_range(setup.ens_member_id or [], fmt='02d')})"
            )
        ),
        "copyright": f"{symbols['copyright']}{words['meteoswiss']}",
    }

    long_name = ""
    short_name = ""
    var_name = ""
    unit = mdata.format("variable_unit")

    if setup.input_variable == "concentration":
        new_config_dct["n_levels"] = 8
        new_config_dct["labels"]["right_middle"]["tc"] = (
            f"{words['level']}:" f" {escape_format_keys(format_level_label(mdata))}"
        )
        var_name = str(words["activity_concentration"])
        if setup.integrate:
            long_name = f"{words['integrated']} {var_name}"
            short_name = (
                f"{words['integrated', 'abbr']} {words['concentration', 'abbr']}"
            )
            variable_rel = (
                f"{words['of', 'fg']} {words['integrated', 'g']}"
                f" {words['activity_concentration']}"
            )
        else:
            long_name = var_name
            short_name = str(words["concentration"])
            variable_rel = f"{words['of', 'fg']} {words['activity_concentration']}"
        new_config_dct["labels"]["right_top"]["lines"].insert(
            0, f"{words['level'].c}:\t{escape_format_keys(format_level_label(mdata))}"
        )

    elif setup.input_variable == "deposition":
        dep_type_word = (
            "total" if setup.deposition_type == "tot" else setup.deposition_type
        )
        var_name = f"{words[dep_type_word, 'f']} {words['surface_deposition']}"
        long_name = var_name
        short_name = str(words["deposition"])
        variable_rel = (
            f"{words['of', 'fg']} {words[dep_type_word, 'g']}"
            f" {words['surface_deposition']}"
        )
        new_config_dct["n_levels"] = 9

    if setup.get_simulation_type() == "deterministic":
        new_config_dct["model_info"] = new_config_dct["labels"]["bottom"][
            "model_info_det"
        ]
        if setup.plot_variable.startswith("affected_area"):
            long_name = f"{words['affected_area']} {variable_rel}"
            if setup.plot_variable == "affected_area_mono":
                new_config_dct["extend"] = "none"
                new_config_dct["n_levels"] = 1

    elif setup.get_simulation_type() == "ensemble":
        new_config_dct["model_info"] = new_config_dct["labels"]["bottom"][
            "model_info_ens"
        ]
        if setup.ens_variable == "minimum":
            long_name = f"{words['ensemble_minimum']} {variable_rel}"
        elif setup.ens_variable == "maximum":
            long_name = f"{words['ensemble_maximum']} {variable_rel}"
        elif setup.ens_variable == "median":
            long_name = f"{words['ensemble_median']} {variable_rel}"
        elif setup.ens_variable == "mean":
            long_name = f"{words['ensemble_mean']} {variable_rel}"
        else:
            new_config_dct.update(
                {
                    "extend": "both",
                    "legend_rstrip_zeros": False,
                    "level_range_style": "int",
                    "level_ranges_align": "left",
                    "mark_field_max": False,
                    "levels_scale": "lin",
                }
            )
            if setup.ens_variable == "probability":
                new_config_dct.update({"n_levels": 9, "d_level": 10})
                new_config_dct["labels"]["right_top"]["lines"].append(
                    f"{words['cloud']}:\t{symbols['geq']} {setup.ens_param_thr}"
                    f" {mdata.format('variable_unit')}"
                )
                short_name = f"{words['probability']}"
                unit = "%"
                long_name = f"{words['probability']} {variable_rel}"
            elif setup.ens_variable in [
                "cloud_arrival_time",
                "cloud_departure_time",
            ]:
                new_config_dct.update({"n_levels": 9, "d_level": 3})
                new_config_dct["labels"]["right_top"]["lines"].append(
                    f"{words['cloud_density'].c}:\t{words['minimum', 'abbr']}"
                    f" {setup.ens_param_thr} {mdata.format('variable_unit')}"
                )
                n_min = setup.ens_param_mem_min or 1
                n_tot = len((setup.ens_member_id or []))
                new_config_dct["labels"]["right_top"]["lines"].append(
                    f"{words['number_of', 'abbr'].c} {words['member', 'pl']}:"
                    f"\t{words['minimum', 'abbr']} {setup.ens_param_mem_min}"
                    r"$\,/\,$"
                    f"{n_tot} ({n_min/(n_tot or 1):.0%})"
                )
                if setup.ens_variable == "cloud_arrival_time":
                    long_name = f"{words['cloud_arrival_time']}"
                    short_name = f"{words['arrival']}"
                elif setup.ens_variable == "cloud_departure_time":
                    long_name = f"{words['cloud_departure_time']}"
                    short_name = f"{words['departure']}"
                unit = f"{words['hour', 'pl']}"
            elif setup.ens_variable == "cloud_occurrence_probability":
                new_config_dct.update({"n_levels": 9, "d_level": 10})
                new_config_dct["labels"]["right_top"]["lines"].append(
                    f"{words['cloud_density'].c}:\t{words['minimum', 'abbr']}"
                    f" {setup.ens_param_thr} {mdata.format('variable_unit')}"
                )
                n_min = setup.ens_param_mem_min or 1
                n_tot = len((setup.ens_member_id or []))
                new_config_dct["labels"]["right_top"]["lines"].append(
                    f"{words['number_of', 'abbr'].c} {words['member', 'pl']}:"
                    f"\t{words['minimum', 'abbr']} {setup.ens_param_mem_min}"
                    r"$\,/\,$"
                    f"{n_tot} ({n_min/(n_tot or 1):.0%})"
                )
                short_name = f"{words['probability']}"
                unit = "%"
                long_name = f"{words['cloud_occurrence_probability']}"

    # SR_TMP <
    if not short_name:
        raise Exception("no short name")
    if not long_name:
        raise Exception("no short name")
    # SR_TMP >

    new_config_dct["labels"]["top"][
        "tl"
    ] = f"{long_name} {words['of']} {mdata.species_name}"
    new_config_dct["labels"]["right_top"]["lines"].insert(
        0, f"{words['input_variable'].c}:\t{capitalize(var_name)}",
    )
    new_config_dct["labels"]["right_middle"]["title"] = short_name
    new_config_dct["labels"]["right_middle"]["title_unit"] = f"{short_name} ({unit})"
    new_config_dct["labels"]["right_middle"]["unit"] = unit

    # Capitalize all labels
    for labels in new_config_dct["labels"].values():
        for name, label in labels.items():
            if name == "lines":
                label = [capitalize(line) for line in label]
            else:
                label = capitalize(label)
            labels[name] = label

    # Colors
    n_levels = new_config_dct["n_levels"]
    extend = new_config_dct.get("extend", "max")
    cmap = new_config_dct.get("cmap", "flexplot")
    if setup.plot_variable == "affected_area_mono":
        colors = (np.array([(200, 200, 200)]) / 255).tolist()
    elif cmap == "flexplot":
        colors = colors_flexplot(n_levels, extend)
    else:
        cmap = mpl.cm.get_cmap(cmap)
        colors = [cmap(i / (n_levels - 1)) for i in range(n_levels)]
    new_config_dct["colors"] = colors

    new_config_dct["markers"] = {
        "max": {
            "marker": "+",
            "color": "black",
            "markersize": 10,
            "markeredgewidth": 1.5,
        },
        "site": {
            "marker": "^",
            "markeredgecolor": "red",
            "markerfacecolor": "white",
            "markersize": 7.5,
            "markeredgewidth": 1.5,
        },
    }

    return BoxedPlotConfig(**new_config_dct)


def fill_box_top(box: TextBoxAxes, plot: BoxedPlot) -> None:
    for position, label in plot.config.labels.get("top", {}).items():
        if position == "tl":
            font_size = plot.config.font_sizes.title_large
        else:
            font_size = plot.config.font_sizes.content_large
        box.text(label, loc=position, fontname=plot.config.font_name, size=font_size)


def fill_box_right_top(box: TextBoxAxes, plot: BoxedPlot) -> None:
    labels = plot.config.labels["right_top"]
    box.text(
        labels["title"],
        loc="tc",
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.title_small,
    )
    box.text_block_hfill(
        labels["lines"],
        dy_unit=-4.0,
        dy_line=2.5,
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.content_small,
    )


# pylint: disable=R0912   # too-many-branches
# pylint: disable=R0913   # too-many-arguments
# pylint: disable=R0914   # too-many-locals
# pylint: disable=R0915   # too-many-statements
def fill_box_right_middle(box: TextBoxAxes, plot: BoxedPlot) -> None:
    """Fill the top box to the right of the map plot."""

    labels = plot.config.labels["right_middle"]
    mdata = plot.config.mdata

    # Box title
    box.text(
        labels["title_unit"],
        loc="tc",
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.title_small,
    )

    # dy_line: float = 3.0
    dy_line: float = 2.5

    w_legend_box: float = 4.0
    h_legend_box: float = 2.0

    dx_legend_box: float = -10
    dx_legend_label: float = -3

    dx_marker: float = dx_legend_box + 0.5 * w_legend_box
    dx_marker_label: float = dx_legend_label - 0.5

    # Vertical position of legend (depending on number of levels)
    dy0_labels = -5.0
    dy0_boxes = dy0_labels - 0.8 * h_legend_box

    # Format level ranges (contour plot legend)
    legend_labels = format_level_ranges(
        levels=plot.levels,
        style=plot.config.level_range_style,
        extend=plot.config.extend,
        rstrip_zeros=plot.config.legend_rstrip_zeros,
        align=plot.config.level_ranges_align,
    )

    # Legend labels (level ranges)
    box.text_block(
        legend_labels[::-1],
        loc="tc",
        dy_unit=dy0_labels,
        dy_line=dy_line,
        dx=dx_legend_label,
        ha="left",
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.content_medium,
        family="monospace",
    )

    # Legend color boxes
    colors = plot.config.colors
    dy = dy0_boxes
    for color in colors[::-1]:
        box.color_rect(
            loc="tc",
            x_anker="left",
            dx=dx_legend_box,
            dy=dy,
            w=w_legend_box,
            h=h_legend_box,
            fc=color,
            ec="black",
            lw=1.0,
        )
        dy -= dy_line

    dy0_markers = dy0_boxes - dy_line * (len(legend_labels) - 0.3)
    dy0_marker = dy0_markers

    # Field maximum marker
    if plot.config.mark_field_max:
        dy_marker_label_max = dy0_marker
        dy0_marker -= dy_line
        dy_max_marker = dy_marker_label_max - 0.7
        assert plot.config.markers is not None  # mypy
        box.marker(
            loc="tc", dx=dx_marker, dy=dy_max_marker, **plot.config.markers["max"],
        )
        if np.isnan(plot.field.fld).all():
            s_val = "NaN"
        else:
            fld_max = np.nanmax(plot.field.fld)
            if 0.001 <= fld_max < 0.01:
                s_val = f"{fld_max:.5f}"
            elif 0.01 <= fld_max < 0.1:
                s_val = f"{fld_max:.4f}"
            elif 0.1 <= fld_max < 1:
                s_val = f"{fld_max:.3f}"
            elif 1 <= fld_max < 10:
                s_val = f"{fld_max:.2f}"
            elif 10 <= fld_max < 100:
                s_val = f"{fld_max:.1f}"
            elif 100 <= fld_max < 1000:
                s_val = f"{fld_max:.0f}"
            else:
                s_val = f"{fld_max:.2E}"
            # s_val += r"$\,$" + labels["unit"]
        s = f"{labels['max']}: {s_val}"
        # s = f"{labels['max']} ({s_val})"
        # s = f"{labels['maximum']}:\n({s_val})"
        box.text(
            s=s,
            loc="tc",
            dx=dx_marker_label,
            dy=dy_marker_label_max,
            ha="left",
            fontname=plot.config.font_name,
            size=plot.config.font_sizes.content_medium,
        )

    # Release site marker
    if plot.config.mark_release_site:
        dy_site_label = dy0_marker
        dy0_marker -= dy_line
        dy_site_marker = dy_site_label - 0.7
        assert plot.config.markers is not None  # mypy
        box.marker(
            loc="tc", dx=dx_marker, dy=dy_site_marker, **plot.config.markers["site"],
        )
        # s = f"{labels['release_site']}"
        # s = f"{labels['site']} ({mdata.release_site_name})"
        s = f"{labels['site']}: {mdata.release_site_name}"
        box.text(
            s=s,
            loc="tc",
            dx=dx_marker_label,
            dy=dy_site_label,
            ha="left",
            fontname=plot.config.font_name,
            size=plot.config.font_sizes.content_medium,
        )


def fill_box_right_bottom(box: TextBoxAxes, plot: BoxedPlot) -> None:
    """Fill the bottom box to the right of the map plot."""

    labels = plot.config.labels["right_bottom"]
    mdata = plot.config.mdata

    # Box title
    box.text(
        s=labels["title"],
        loc="tc",
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.title_small,
    )

    # Release site coordinates
    lat = Degrees(mdata.release_site_lat.value)
    lon = Degrees(mdata.release_site_lon.value)
    lat_deg = labels["lat_deg_fmt"].format(d=lat.degs(), m=lat.mins(), f=lat.frac())
    lon_deg = labels["lon_deg_fmt"].format(d=lon.degs(), m=lon.mins(), f=lon.frac())

    # SR_TMP < TODO clean this up, especially for ComboMetaData (units messed up)!
    height = mdata.format("release_height", add_unit=True)
    rate = mdata.format("release_rate", add_unit=True)
    mass = mdata.format("release_mass", add_unit=True)
    substance = mdata.format("species_name", join_combo=" / ")
    half_life = mdata.format("species_half_life", add_unit=True)
    deposit_vel = mdata.format("species_deposit_vel", add_unit=True)
    sediment_vel = mdata.format("species_sediment_vel", add_unit=True)
    washout_coeff = mdata.format("species_washout_coeff", add_unit=True)
    washout_exponent = mdata.format("species_washout_exponent")
    # SR_TMP >

    info_blocks = dedent(
        f"""\
        {labels['site']}:\t{mdata.release_site_name}
        {labels['latitude']}:\t{lat_deg}
        {labels['longitude']}:\t{lon_deg}
        {labels['height']}:\t{height}

        {labels['start']}:\t{mdata.release_start}
        {labels['end']}:\t{mdata.release_end}
        {labels['rate']}:\t{rate}
        {labels['mass']}:\t{mass}

        {labels['name']}:\t{substance}
        {labels['half_life']}:\t{half_life}
        {labels['deposit_vel']}:\t{deposit_vel}
        {labels['sediment_vel']}:\t{sediment_vel}
        {labels['washout_coeff']}:\t{washout_coeff}
        {labels['washout_exponent']}:\t{washout_exponent}
        """
    )

    # Add lines bottom-up (to take advantage of baseline alignment)
    box.text_blocks_hfill(
        info_blocks,
        dy_unit=-4.0,
        dy_line=2.5,
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.content_small,
    )


def fill_box_bottom(box: TextBoxAxes, plot: BoxedPlot) -> None:
    """Fill the box to the bottom of the map plot."""

    labels = plot.config.labels["bottom"]

    # FLEXPART/model info
    s = plot.config.model_info
    box.text(
        s=s,
        loc="tl",
        dx=-0.7,
        dy=0.5,
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.content_small,
    )

    # MeteoSwiss Copyright
    box.text(
        s=labels["copyright"],
        loc="tr",
        dx=0.7,
        dy=0.5,
        fontname=plot.config.font_name,
        size=plot.config.font_sizes.content_small,
    )


def plot_fields(
    field_lst_lst: Sequence[Sequence[Field]],
    mdata_lst_lst: Sequence[Sequence[MetaData]],
    dry_run: bool = False,
    *,
    write: bool = True,
) -> Iterator[Tuple[str, Optional[BoxedPlot]]]:
    """Create plots while yielding them with the plot file path one by one."""
    path_formatter = FilePathFormatter()
    for field_lst, mdata_lst in zip(field_lst_lst, mdata_lst_lst):
        setup = InputSetupCollection(
            [var_setup for field in field_lst for var_setup in field.var_setups]
        ).compress()
        out_file_path = path_formatter.format(setup)
        map_conf_lst = [create_map_conf(field) for field in field_lst]
        if dry_run:
            plot = None
        else:
            configs = [
                create_plot_config(setup, WORDS, SYMBOLS, mdata) for mdata in mdata_lst
            ]
            plot = BoxedPlot(field_lst, configs, map_conf_lst)
            plot_add_text_boxes(plot)
            plot_add_markers(plot)
            plot.save(out_file_path, write=write)
        yield out_file_path, plot


def plot_add_text_boxes(plot: BoxedPlot) -> None:
    layout = plot.layout  # SR_TMP
    plot.add_text_box("top", layout.rect_top, fill_box_top)
    plot.add_text_box("right_top", layout.rect_right_top, fill_box_right_top)
    plot.add_text_box("right_middle", layout.rect_right_middle, fill_box_right_middle)
    plot.add_text_box("right_bottom", layout.rect_right_bottom, fill_box_right_bottom)
    plot.add_text_box("bottom", layout.rect_bottom, fill_box_bottom, frame_on=False)


def plot_add_markers(plot: BoxedPlot) -> None:
    config = plot.config

    if config.mark_release_site:
        assert isinstance(config.mdata.release_site_lon.value, float)  # mypy
        assert isinstance(config.mdata.release_site_lat.value, float)  # mypy
        assert config.markers is not None  # mypy
        plot.add_marker(
            lat=config.mdata.release_site_lat.value,
            lon=config.mdata.release_site_lon.value,
            **config.markers["site"],
        )

    if config.mark_field_max:
        assert config.markers is not None  # mypy
        try:
            max_lat, max_lon = plot.field.locate_max()
        except FieldAllNaNError:
            warnings.warn("skip maximum marker (all-nan field)")
        else:
            plot.ax_map.marker(lat=max_lat, lon=max_lon, **config.markers["max"])


def colors_flexplot(n_levels: int, extend: str) -> Sequence[ColorType]:

    color_under = "darkgray"
    color_over = "lightgray"

    # def rgb(*vals):
    #     return np.array(vals, float) / 255

    # colors_core_8_old = [
    #     rgb(224, 196, 172),
    #     rgb(221, 127, 215),
    #     rgb(99, 0, 255),
    #     rgb(100, 153, 199),
    #     rgb(34, 139, 34),
    #     rgb(93, 255, 2),
    #     rgb(199, 255, 0),
    #     rgb(255, 239, 57),
    # ]
    colors_core_8 = [
        "bisque",
        "violet",
        "rebeccapurple",
        "cornflowerblue",
        "forestgreen",
        "yellowgreen",
        "greenyellow",
        "yellow",
    ]

    colors_core_7 = [colors_core_8[i] for i in (0, 1, 2, 3, 5, 6, 7)]
    colors_core_6 = [colors_core_8[i] for i in (1, 2, 3, 4, 5, 7)]
    colors_core_5 = [colors_core_8[i] for i in (1, 2, 4, 5, 7)]
    colors_core_4 = [colors_core_8[i] for i in (1, 2, 4, 7)]

    try:
        colors_core = {
            5: colors_core_4,
            6: colors_core_5,
            7: colors_core_6,
            8: colors_core_7,
            9: colors_core_8,
        }[n_levels]
    except KeyError:
        raise ValueError(f"n_levels={n_levels}")

    if extend == "none":
        return colors_core
    elif extend == "min":
        return [color_under] + colors_core
    elif extend == "max":
        return colors_core + [color_over]
    elif extend == "both":
        return [color_under] + colors_core + [color_over]
    raise ValueError(f"extend='{extend}'")


def escape_format_keys(s: str) -> str:
    return s.replace("{", "{{").replace("}", "}}")


def format_level_label(mdata: MetaData) -> str:
    unit = mdata.variable_level_bot_unit.value
    if mdata.variable_level_top_unit.value != unit:
        raise Exception(
            "inconsistent level units",
            mdata.variable_level_bot_unit,
            mdata.variable_level_top_unit,
        )
    assert isinstance(unit, str)  # mypy
    level = format_vertical_level_range(
        mdata.variable_level_bot.value, mdata.variable_level_top.value, unit
    )
    if not level:
        return ""
    return f"{format_unit(level)}"


def format_vertical_level_range(
    value_bottom: Union[float, Sequence[float]],
    value_top: Union[float, Sequence[float]],
    unit: str,
) -> Optional[str]:

    if (value_bottom, value_top) == (-1, -1):
        return None

    def fmt(bot, top):
        return f"{bot:g}" + r"$-$" + f"{top:g} {unit}"

    try:
        # One level range (early exit)
        return fmt(value_bottom, value_top)
    except TypeError:
        pass

    # Multiple level ranges
    assert isinstance(value_bottom, Collection)  # mypy
    assert isinstance(value_top, Collection)  # mypy
    bots = sorted(value_bottom)
    tops = sorted(value_top)
    if len(bots) != len(tops):
        raise Exception(f"inconsistent no. levels: {len(bots)} != {len(tops)}")
    n = len(bots)
    if n == 2:
        # Two level ranges
        if tops[0] == bots[1]:
            return fmt(bots[0], tops[1])
        else:
            return f"{fmt(bots[0], tops[0])} + {fmt(bots[1], tops[1])}"
    elif n == 3:
        # Three level ranges
        if tops[0] == bots[1] and tops[1] == bots[2]:
            return fmt(bots[0], tops[2])
        else:
            raise NotImplementedError("3 non-continuous level ranges")
    else:
        raise NotImplementedError(f"{n} sets of levels")


def format_integr_period(
    mdata: "MetaData", setup: InputSetup, words: TranslatedWords, cap: bool = False
) -> str:
    integr_type = get_integr_type(setup)
    if integr_type == "mean":
        operation = words["averaged_over"].s
    elif integr_type == "sum":
        operation = words["summed_over"].s
    elif integr_type == "accum":
        operation = words["accumulated_over"].s
    start = mdata.simulation_integr_start.value
    now = mdata.simulation_now.value
    assert isinstance(start, datetime)  # mypy
    assert isinstance(now, datetime)  # mypy
    period = now - start
    hours = int(period.total_seconds() / 3600)
    minutes = int((period.total_seconds() / 60) % 60)
    s = f"{operation} {hours:d}:{minutes:02d}$\\,$h"
    if cap:
        s = s[0].upper() + s[1:]
    return s


def format_coord_label(direction: str, words: TranslatedWords, symbols: Words) -> str:
    deg_unit = f"{symbols['deg']}{symbols['short_space']}"
    min_unit = f"'{symbols['short_space']}"
    dir_unit = words[direction, "abbr"]
    if direction == "north":
        deg_dir_unit = words["degN"]
    elif direction == "east":
        deg_dir_unit = words["degE"]
    else:
        raise NotImplementedError("unit for direction", direction)
    return f"{{d}}{deg_unit}{{m}}{min_unit}{dir_unit} ({{f:.4f}}{deg_dir_unit})"