# -*- coding: utf-8 -*-
"""
Plots.
"""
import cartopy
import logging as log
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import os.path
import re

from matplotlib import ticker
from textwrap import dedent

from .utils_dev import ipython  #SR_DEV

mpl.use('Agg')  # Prevent ``couldn't connect to display`` error


class FlexPlotter:
    """Create one or more FLEXPLART plots of a certain type.

    Attributes:
        <TODO>

    Methods:
        <TODO>

    """

    def __init__(self, type_):
        """Initialize instance of FlexPlotter.

        Args:
            type_ (str): Type of plot.

        """
        self.type_ = type_

    def run(self, data, file_path_fmt):
        """Create plots.

        Args:
            data (FlexData): All necessary data (grid, fields, attrs)
                required for the plot, read from a FLEXPART file.

            file_path_fmt (str): Format string of output file path.
                Must contain all necessary format keys to avoid that
                multiple files have the same name, but can be a plain
                string if no variable assumes more than one value.

        Yields:
            str: Output file paths.

        """
        self.data = data
        self.file_path_fmt = file_path_fmt

        if self.type_ == 'concentration':
            for path in self._run_concentration():
                yield path
        else:
            raise NotImplementedError(f"plot type '{self.type_}'")

    def _run_concentration(self):
        """Create one or more concentration plots."""

        # Check availability of required field type
        field_type = '3D'
        field_types_all = self.data.field_types()
        if field_type not in field_types_all:
            raise Exception(
                f"missing field type '{field_type}' among {field_types_all}")

        # Collect field keys
        restrictions = {"field_types": [field_type]}
        keys = self.data.field_keys(**restrictions)

        # Check output file path for format keys
        self.check_file_path_fmt(restrictions)

        # Create plots
        file_paths = []
        _s = 's' if len(keys) > 1 else ''
        print(f"create {len(keys)} concentration plot{_s}")
        for i_key, key in enumerate(keys):
            file_path = self.format_file_path(key)
            _w = len(str(len(keys)))
            print(f" {i_key+1:{_w}}/{len(keys)}  {file_path}")

            kwargs = {
                'rlat': self.data.rlat,
                'rlon': self.data.rlon,
                'fld': self.data.field(key),
                'attrs': {},  #SR_TMP
            }

            FlexPlotConcentration(**kwargs).save(file_path)

            yield file_path

    def check_file_path_fmt(self, restrictions):
        """Check output file path for necessary variables format keys.

        If a variable (e.g., species id, level index) assumes multiple
        values, the file path must contain a corresponding format key,
        otherwise multiple output files will share the same name and
        overwrite each other.

        Args:
            restrictions (dict): Restrictions to field keys, i.e.,
                explicitly selected values of some variables.

        """

        def _check_file_path_fmt__core(name):
            """Check if the file path contains a necessary variable."""
            values = set(getattr(self.data, f'{name}s')(**restrictions))
            rx = re.compile(r'\{' + name + r'(:.*)?\}')
            if len(values) > 1 and not rx.search(self.file_path_fmt):
                raise Exception(
                    f"output file path '{self.file_path_fmt}' must contain"
                    f" format key '{fmt_key}' to plot {len(values)} different"
                    f" {name.replace('_', ' ')}s {sorted(values)}")

        _check_file_path_fmt__core('age_ind')
        _check_file_path_fmt__core('relpt_ind')
        _check_file_path_fmt__core('time_ind')
        _check_file_path_fmt__core('level_ind')
        _check_file_path_fmt__core('species_id')
        _check_file_path_fmt__core('field_type')

    def format_file_path(self, key):
        """Create output file path for a given field key.

        Args:
            key (namedtuple): Field key.

        """
        return self.file_path_fmt.format(**key._asdict())


#SR_TMP<
class ColorStr:

    def __init__(self, s, c):
        self.s = s
        self.c = c

    def __repr__(self):
        return f"{self.__class__.__name__}({self.s}, {self.c})"

    def __str__(self):
        return self.s

    def split(self, *args, **kwargs):
        return [
            self.__class__(s, self.c)
            for s in str.split(self.s, *args, **kwargs)
        ]

    def strip(self, *args, **kwargs):
        s = str.strip(self.s, *args, **kwargs)
        return self.__class__(s, self.c)


#SR_TMP>


class FlexPlotConcentration:
    """FLEXPART plot of particle concentration at a certain level.

    Attributes:
        <TODO>

    Methods:
        <TODO>

    """

    def __init__(self, rlat, rlon, fld, attrs, conf=None):
        """Initialize instance of FlexPlotConcentration.

        Args:
            rlat (ndarray[float]): Rotated latitude (1d).

            rlon (ndarray[float]): Rotated longitude (1d).

            fld (ndarray[float, float]): Concentration field (2d).

            attrs (dict): Attributes from the FLEXPART NetCDF file
                (gloabl, variable-specific, etc.).

            conf (dict, optional): Plot configuration. Defaults to None.

        """
        self.rlat = rlat
        self.rlon = rlon
        self.fld = np.where(fld > 0, fld, np.nan)
        self.attrs = attrs
        self.conf = {} if conf is None else conf

        #SR_TMP< TODO Extract from NetCDF file
        self.attrs['rotated_pole'] = {
            'grid_north_pole_latitude': 43.0,
            'grid_north_pole_longitude': -170.0,
        }
        #SR_TMP>

        self.levels = None
        self.colors = None

        self._run()

    def _run(self):

        # Prepare plot
        self.fig = plt.figure(figsize=(12, 9))
        pollat = self.attrs['rotated_pole']['grid_north_pole_latitude']
        pollon = self.attrs['rotated_pole']['grid_north_pole_longitude']
        self.ax_map = FlexAxesMapRotatedPole(
            self.fig, self.rlat, self.rlon, pollat, pollon)

        # Plot particle concentration field
        self.map_add_particle_concentrations()

        # Add text boxes around plot
        self.fig_add_text_boxes()
        self.fill_box_top()
        self.fill_box_top_right()
        self.fill_box_bottom_right()

    def map_add_particle_concentrations(self):
        """Plot the particle concentrations onto the map."""

        #SR_TMP>
        levels_log10 = np.arange(-1, 9.1, 1)
        cmap = 'terrain_r'
        extend = 'max'
        #SR_TMP>

        fld_log10 = np.log10(self.fld)

        if isinstance(cmap, str):
            cmap = mpl.cm.get_cmap(cmap)

        colors = cmap(np.linspace(0, 1, len(levels_log10) + 1))
        cmap = mpl.colors.ListedColormap(colors[1:-1])
        cmap.set_under(colors[0])
        cmap.set_over(colors[-1])

        handle = self.ax_map.plot_contourf(
            fld_log10,
            levels=levels_log10,
            cmap=cmap,
            extend=extend,
        )

        # Store some properties
        self.levels = 10**levels_log10
        self.extend = 'max'
        self.colors = {
            'none': colors[1:-1],
            'min': colors[:-1],
            'max': colors[1:],
            'both': colors[:],
        }[self.extend]
        self.cmap = cmap

        return handle

    def fig_add_text_boxes(self, h_rel=0.1, w_rel=0.25, pad_hor_rel=0.015):
        """Add empty text boxes to the figure around the map plot.

        Args:
            h_rel (float, optional): Height of top box as a fraction of
                the height of the map plot. Defaults to <TODO>.

            w_rel (float, optional): Width of the right boxes as a
                fraction of the width of the map plot. Default to <TODO>.

            pad_hor_rel (float, optional): Padding between map plot and
                the text boxes as a fraction of the map plot width. The
                same absolute padding is used in the horizontal and
                vertical direction. Defaults to <TODO>.

        """
        self.ax_ref = self.ax_map.ax  #SR_TMP

        # Freeze the map plot in order to fix it's coordinates (bbox)
        self.fig.canvas.draw()

        # Obtain aspect ratio of figure
        fig_pxs = self.fig.get_window_extent()
        fig_aspect = fig_pxs.width/fig_pxs.height

        # Get map dimensions in figure coordinates
        w_map, h_map = ax_dims_fig_coords(self.fig, self.ax_ref)

        # Relocate the map close to the lower left corner
        x0_map, y0_map = 0.05, 0.05
        self.ax_ref.set_position([x0_map, y0_map, w_map, h_map])

        # Determine height of top box and width of right boxes
        w_box = w_rel*w_map
        h_box = h_rel*h_map

        # Determine padding between plot and boxes
        pad_hor = pad_hor_rel*w_map
        pad_ver = pad_hor*fig_aspect

        # Add axes for text boxes (one on top, two to the right)
        h_rel_box_top = 0.4
        self.axs_box = np.array([
            FlexAxesTextBox(
                self.fig, self.ax_map.ax, [
                    x0_map,
                    y0_map + pad_ver + h_map,
                    w_map + pad_hor + w_box,
                    h_box,
                ]),
            FlexAxesTextBox(
                self.fig, self.ax_map.ax, [
                    x0_map + pad_hor + w_map,
                    y0_map + 0.5*pad_ver + (1.0 - h_rel_box_top)*h_map,
                    w_box,
                    h_rel_box_top*h_map - 0.5*pad_ver,
                ]),
            FlexAxesTextBox(
                self.fig, self.ax_map.ax, [
                    x0_map + pad_hor + w_map,
                    y0_map,
                    w_box,
                    (1.0 - h_rel_box_top)*h_map - 0.5*pad_ver,
                ]),
        ])

    def fill_box_top(self):
        """Fill the box above the map plot."""
        box = self.axs_box[0]

        #SR_TMP< TODO obtain from NetCDF attributes
        varname = 'Concentration'
        level_str = '500 $\endash$ 2000 m AGL'
        species = 'Cs-137'
        timestep_fmtd = '2019-05-28 03:00 UTC'
        release_site = 'Goesgen'
        tz_str = 'T0 + 03:00 h'
        #SR_TMP>

        # Top left: variable and level
        s = f"{varname} {level_str}"
        box.text('tl', s, size='xx-large')

        # Top center: species
        s = f"{species}"
        box.text('tc', s, size='xx-large')

        # Top right: datetime
        s = f"{timestep_fmtd}"
        box.text('tr', s, size='xx-large')

        # Bottom left: release site
        s = f"Release site: {release_site}"
        box.text('bl', s, size='large')

        # Bottom right: time zone
        s = f"{tz_str}"
        box.text('br', s, size='large')

    def fill_box_top_right(self):
        """Fill the box to the top-right of the map plot."""
        box = self.axs_box[1]

        #SR_TMP<
        varname = 'Concentration'
        unit_fmtd = 'Bq m$^-3$'
        #SR_TMP>

        # Add box title
        box.text('tc', f"{varname} ({unit_fmtd})", size='large')

        # Format level ranges (contour plot legend)
        labels = self._format_level_ranges()

        #SR_TMP<
        color_labels = [ColorStr('###', c) for c in self.colors]
        block = list(zip(color_labels, labels))
        color_labels[0].split('X', 1)
        #SR_TMP>

        box.text_block_hfill(
            'b',
            block,
            dy0=2.0,
            dy_line=2.5,
            dx=2.0,
            size='medium',
            family='monospace',
        )

    def _format_level_ranges(self):
        """Format the levels ranges for the contour plot legend."""

        def format_label(lvl0, lvl1):

            def format_level(lvl):
                return '' if lvl is None else f"{lvl:g}".strip()

            return f"{format_level(lvl0):>6} > {format_level(lvl1):<6}"

        labels = []

        # 'Under' color
        if self.extend in ('min', 'both'):
            labels.append(format_label(None, self.levels[0]))

        # Regular colors
        for lvl0, lvl1 in zip(self.levels[:-1], self.levels[1:]):
            labels.append(format_label(lvl0, lvl1))

        # 'Over' color
        if self.extend in ('max', 'both'):
            labels.append(format_label(None, self.levels[-1]))

        #SR_TMP<
        assert len(labels) == len(self.colors), \
            f'{len(labels)} != {len(self.colors)}'
        #SR_TMP>

        return labels

    def fill_box_bottom_right(self):
        """Fill the box to the bottom-right of the map plot."""
        box = self.axs_box[2]

        #SR_TMP<
        lat_mins = (47, 22)
        lat_frac = 47.37
        lon_mins = (7, 58)
        lon_frac = 7.97
        height = 100
        start_fmtd = "2019-05-28 00:00 UTC"
        end_fmtd = "2019-05-28 08:00 UTC"
        rate = 34722.2
        mass = 1e9
        substance_fmtd = 'Cs$\endash$137'
        half_life = 30.0
        depos_vel = 1.5e-3
        sedim_vel = 0.0
        wash_coeff = 7.0e-5
        wash_exp = 0.8
        #SR_TMP>

        # Add box title
        box.text('tc', 'Release', size='large')

        lat_fmtd = (
            f"{lat_mins[0]}$^\circ$ {lat_mins[1]}' N"
            f" (={lat_frac}$^\circ$ N)")
        lon_fmtd = (
            f"{lon_mins[0]}$^\circ$ {lon_mins[1]}' E"
            f" (={lon_frac}$^\circ$ E)")

        info_blocks = dedent(
            f"""\
            Latitude:\t{lat_fmtd}
            Longitude:\t{lon_fmtd}
            Height:\t{height} m AGL

            Start:\t{start_fmtd}
            End:\t{end_fmtd}
            Rate:\t{rate} Bq s$^{{-1}}$
            Total Mass:\t{mass} Bq

            Substance:\t{substance_fmtd}
            Half-Life:\t{half_life} years
            Deposit. Vel.:\t{depos_vel} m s$^{{-1}}$
            Sediment. Vel.:\t{sedim_vel} m s$^{{-1}}$
            Washout Coeff.:\t{wash_coeff} s$^{{-1}}$
            Washout Exponent:\t{wash_exp}
            """)

        # Add lines bottom-up (to take advantage of baseline alignment)
        dy = 2.75
        box.text_blocks_hfill(
            'b', dy_line=dy, blocks=info_blocks, reverse=True, size='small')

    def save(self, file_path, format=None):
        """Save the plot to disk.

        Args:
            file_path (str): Output file name, incl. path.

            format (str): Plot format (e.g., 'png', 'pdf'). Defaults to
                None. If ``format`` is None, the plot format is derived
                from the extension of ``file_path``.

        """
        if format is None:
            ext = os.path.splitext(file_path)[1].lower()
            if ext not in ['.pdf', '.png']:
                raise ValueError(
                    f"Cannot derive format from extension '{ext}'"
                    f"derived from '{os.path.basename(file_path)}'")
            format = ext[1:]
        self.fig.savefig(
            file_path,
            facecolor=self.fig.get_facecolor(),
            edgecolor=self.fig.get_edgecolor(),
            bbox_inches='tight',
            pad_inches=0.15,
        )
        plt.close(self.fig)


class FlexAxesMapRotatedPole():
    """Map plot axes for FLEXPART plot for rotated-pole data.

    Attributes:
        <TODO>

    Methods:
        <TODO>

    """

    def __init__(self, fig, rlat, rlon, pollat, pollon, **conf):
        """Initialize instance of FlexAxesMapRotatedPole.

        Args:
            fig (Figure): Figure to which to map axes is added.

            rlat (ndarray[float]): Rotated latitude coordinates.

            rlon (ndarray[float]): Rotated longitude coordinates.

            pollat (float): Latitude of rotated pole.

            pollon (float): Longitude of rotated pole.

            **conf: Various plot configuration parameters.

        """
        self.fig = fig
        self.rlat = rlat
        self.rlon = rlon
        self.conf = conf

        # Determine zorder of unique plot elements, from low to high
        zorders_const = [
            'map',
            'grid',
            'fld',
        ]
        d0, dz = 1, 1
        self.zorder = {e: d0 + i*dz for i, e in enumerate(zorders_const)}

        self.prepare_projections(pollat, pollon)

        self.ax = self.fig.add_subplot(projection=self.proj_plot)

        self.ax.set_extent(
            self.padded_bbox(pad_rel=0.01),
            self.proj_data,
        )

        self.ax.gridlines(
            linestyle=':',
            linewidth=1,
            color='black',
            zorder=self.zorder['grid'],
        )

        self.add_geography('50m')
        #self.add_geography('10m')

        self.add_data_domain_outline()

    def prepare_projections(self, pollat, pollon):
        """Prepare projections to transform the data for plotting.

        Args:
            pollat (float): Lattitude of rorated pole.

            pollon (float): Longitude of rotated pole.

        """

        # Projection of input data: Rotated Pole
        self.proj_data = cartopy.crs.RotatedPole(
            pole_latitude=pollat, pole_longitude=pollon)

        # Projection of plot
        clon = 180 + pollon
        self.proj_plot = cartopy.crs.TransverseMercator(central_longitude=clon)

        # Geographical lat/lon arrays
        self.proj_geo = cartopy.crs.PlateCarree()
        rlat2d, rlon2d = np.meshgrid(self.rlat, self.rlon)
        self.lon2d, self.lat2d, _ = self.proj_geo.transform_points(
            self.proj_data, rlat2d, rlon2d).T

    def padded_bbox(self, pad_rel=0.0):
        """Compute the bounding box based on rlat/rlon with padding.

        Args:
            pad_rel (float, optional): Padding between the bounding box
                of the data and that of the plot, specified as a
                fraction of the extent of the bounding box of the data
                in the respective direction (horizontal or vertical).
                Can be negative. Defaults to 0.0.

        """
        # Default: data domain
        bbox = [self.rlon[0], self.rlon[-1], self.rlat[0], self.rlat[-1]]

        # Get padding factor -- either a single number, or a (x, y) tuple
        bbox_pad_rel = self.conf.get('bbox_pad_rel', pad_rel)
        try:
            pad_fact_x, pad_fact_y = bbox_pad_rel
        except TypeError:
            pad_fact_x, pad_fact_y = [bbox_pad_rel]*2

        # Add padding: grow (or shrink) bbox by a factor
        dlon = bbox[1] - bbox[0]
        dlat = bbox[3] - bbox[2]
        padx = dlon*pad_fact_x
        pady = dlon*pad_fact_y
        bbox_pad = np.array([-padx, padx, -pady, pady])
        bbox += bbox_pad

        return bbox

    def add_geography(self, scale):
        """Add geographic elements: coasts, countries, colors, ...

        Args:
            scale (str): Spatial scale of elements, e.g., '10m', '50m'.

        """

        self.ax.coastlines(resolution=scale)

        self.ax.background_patch.set_facecolor(cartopy.feature.COLORS['water'])

        self.ax.add_feature(
            cartopy.feature.NaturalEarthFeature(
                category='cultural',
                name='admin_0_countries_lakes',
                scale=scale,
                edgecolor='black',
                facecolor='white',
            ),
            zorder=self.zorder['map'],
        )

    def add_data_domain_outline(self):
        """Add domain outlines to map plot."""

        lon0, lon1 = self.rlon[[0, -1]]
        lat0, lat1 = self.rlat[[0, -1]]
        xs = [lon0, lon1, lon1, lon0, lon0]
        ys = [lat0, lat0, lat1, lat1, lat0]

        self.ax.plot(xs, ys, transform=self.proj_data, c='black', lw=1)

    def plot_contourf(self, fld, **kwargs):
        """Plot a color contour field on the map.

        Args:
            fld (ndarray[float, float]): Field to plot.

            **kwargs: Arguments passed to ax.contourf().

        Returns:
            Plot handle.

        """
        p = self.ax.contourf(
            self.rlon,
            self.rlat,
            fld,
            transform=self.proj_data,
            zorder=self.zorder['fld'],
            **kwargs,
        )

        #SR_TMP<
        #-self.fig.colorbar(p, orientation='horizontal')
        #SR_TMP>

        return p


class FlexAxesTextBox:
    """Text box axes for FLEXPART plot.

    Attributes:
        <TODO>

    Methods:
        <TODO>

    """

    def __init__(self, fig, ax_ref, rect):
        """Initialize instance of FlexAxesTextBox.

        Args:
            fig (Figure): Figure to which to add the text box axes.

            ax_ref (Axis): Reference axes.

            rect (list): Rectangle [left, bottom, width, height].

        """

        self.fig = fig
        self.ax_ref = ax_ref

        self.ax = self.fig.add_axes(rect)
        self.ax.axis('off')

        self.draw_box()

        self.compute_unit_distances()

        # Text baseline (for debugging)
        self._show_baseline = False
        self._baseline_kwargs_default = {
            'color': 'black',
            'linewidth': 0.5,
        }
        self._baseline_kwargs = self._baseline_kwargs_default

    def draw_box(self, x=0.0, y=0.0, w=1.0, h=1.0, fc='white', ec='black'):
        """Draw a box onto the axes."""
        self.ax.add_patch(
            mpl.patches.Rectangle(
                xy=(x, y),
                width=w,
                height=h,
                transform=self.ax.transAxes,
                fc=fc,
                ec=ec,
            ))

    def compute_unit_distances(self, unit_w_map_rel=0.01):
        """Compute unit distances in x and y for text positioning.

        To position text nicely inside a box, it is handy to have
        unit distances of absolute length to work with that are
        independent of the size of the box (i.e., axes). This method
        computes such distances as a fraction of the width of the
        map plot.

        Args:
            unit_w_map_rel (float, optional): Fraction of the width
                of the map plot that corresponds to one unit distance.
                Defaults to 0.01.

        """
        w_map_fig, _ = ax_dims_fig_coords(self.fig, self.ax_ref)
        w_box_fig, h_box_fig = ax_dims_fig_coords(self.fig, self.ax)

        self.dx = unit_w_map_rel*w_map_fig/w_box_fig
        self.dy = unit_w_map_rel*w_map_fig/h_box_fig

    def text(self, loc, s, dx=None, dy=None, **kwargs):
        """Add text positioned relative to a reference location.

        Args:
            loc (int|str): Reference location parameter used to
                initialize an instance of ``BoxLocation``.

            s (str): Text string.

            dx (float, optional): Horizontal offset in number of unit
                distances.  Can be negative. Defaults to 0.0.

            dy (float, optional): Vertical offset in number of unit
                distances.  Can be negative. Defaults to 0.0.

            **kwargs: Formatting options passed to ax.text().

        """
        if dx is None:
            dx = 0.0
        if dy is None:
            dy = 0.0

        # Derive location variables from parameter
        loc = BoxLocation(loc)
        ha = loc.get_ha()
        va = loc.get_va()
        x0 = loc.get_x0(self.dx)
        y0 = loc.get_y0(self.dy)

        # Text position
        x = x0 + dx*self.dx
        y = y0 + dy*self.dy

        # Add alignment parameters, unless specified in input kwargs
        kwargs['ha'] = kwargs.get('horizontalalignment', kwargs.get('ha', ha))
        kwargs['va'] = kwargs.get('verticalalignment', kwargs.get('va', va))

        if kwargs['va'] == 'top_baseline':
            # SR_NOTE: [2019-06-11]
            # Ideally, we would like to align text by a `top_baseline`,
            # analogous to baseline and center_baseline, which does not
            # depend on the height of the letters (e.g., '$^\circ$'
            # lifts the top of the text, like 'g' at the bottom). This
            # does not exist, however, and attempts to emulate it by
            # determining the line height (e.g., draw an 'M') and then
            # shifting y accordingly (with `baseline` alignment) were
            # not successful.
            raise NotImplementedError(f"verticalalignment='{kwargs['vs']}'")

        #SR_TMP<
        if isinstance(s, ColorStr):
            kwargs['color'] = s.c
        #SR_TMP>

        # Add text
        self.ax.text(x=x, y=y, s=s, **kwargs)

        if self._show_baseline:
            # Draw a horizontal line at the text baseline
            self.ax.axhline(y, **self._baseline_kwargs)

    def text_block(self, loc, block, colors=None, **kwargs):
        """Add a text block comprised of multiple lines.

        Args:
            loc (int|str): Reference location. For details see
                ``FlexAxesTextBox.text``.

            block (list[str]): Text block.

            colors (list[<color>], optional): Line-specific colors.
                Defaults to None. If not None, must have same length
                as ``block``. Omit individual lines with None.

            **kwargs: Positioning and formatting options passed to
                ``FlexAxesTextBox.text_blocks``.

        """
        self.text_blocks(loc, [block], colors=[colors], **kwargs)

    def text_blocks(
            self,
            loc,
            blocks,
            *,
            dy0=None,
            dy_line=None,
            dy_block=None,
            reverse=False,
            colors=None,
            **kwargs):
        """Add multiple text blocks.

        Args:
            loc (int|str): Reference location. For details see
                ``FlexAxesTextBox.text``.

            blocks (list[list[str]]): List of text blocks, each of
                which constitutes a list of lines.

            dy0 (float, optional): Initial vertical offset in number
                of unit distances. Can be negative. Defaults to
                ``dy_line``.

            dy_line (float, optional): Incremental vertical offset
                between lines. Can be negative. Defaults to 2.5.

            dy_block (float, optional): Incremental vertical offset
                between blocks of lines. Can be negative. Defaults to
                ``dy_line``.

            dx (float, optional): Horizontal offset in number
                of unit distances. Can be negative. Defaults to 0.0.

            reverse (bool, optional): If True, revert the blocka and
                line order. Defaults to False. Note that if line-
                specific colors are passed, they must be in the same
                order as the unreversed blocks.

            colors (list[list[<color>]], optional): Line-specific
                colors in each block. Defaults to None. If not None,
                must have same shape as ``blocks``. Omit individual
                blocks or lines in blocks with None.

            **kwargs: Formatting options passed to ``ax.text``.

        """
        if dy_line is None:
            dy_line = 2.5
        if dy0 is None:
            dy0 = dy_line
        if dy_block is None:
            dy_block = dy_line

        # Fetch text color (fall-back if no line-specific color)
        default_color = kwargs.pop('color', kwargs.pop('c', 'black'))

        # Rename colors variable
        colors_blocks = colors
        del colors

        # Prepare line colors
        if colors_blocks is None:
            colors_blocks = [None]*len(blocks)
        elif len(colors_blocks) != len(blocks):
            raise ValueError(
                f"colors must have same length as blocks:"
                f"  {len(colors)} != {len(blocks)}")
        for i, block in enumerate(blocks):
            if colors_blocks[i] is None:
                colors_blocks[i] = [None]*len(block)
            elif len(colors_blocks) != len(blocks):
                ith = f"{i}{({1: 'st', 2: 'nd', 3: 'rd'}.get(i, 'th'))}"
                raise ValueError(
                    f"colors of {ith} block must have same length as block:"
                    f"  {len(colors_blocks[i])} != {len(block)}")
            for j in range(len(block)):
                if colors_blocks[i][j] is None:
                    colors_blocks[i][j] = default_color

        if reverse:
            # Revert order of blocks and lines
            def revert(lsts):
                return [[l for l in lst[::-1]] for lst in lsts[::-1]]

            blocks = revert(blocks)
            colors_blocks = revert(colors_blocks)

        dy = dy0
        for i, block in enumerate(blocks):
            for j, line in enumerate(block):
                self.text(
                    loc,
                    s=line,
                    dy=dy,
                    color=colors_blocks[i][j],
                    **kwargs,
                )
                dy += dy_line
            dy += dy_block

    def text_block_hfill(self, loc_y, block, **kwargs):
        """Single block of horizontally filled lines.

        See ``FlexAxesTextBox.text_blocks_hfill`` for details.
        """
        self.text_blocks_hfill(loc_y, [block], **kwargs)

    def text_blocks_hfill(self, loc_y, blocks, **kwargs):
        """Add blocks of horizontally-filling lines.

        Lines are split at a tab character ('\t'), with the text before
        the tab left-aligned, and the text after right-aligned.

        Args:
            locy (int|str): Vertical reference location. For details
                see ``FlexAxesTextBox.text`` (vertical component
                only).

            blocks (str | list[ str | list[ str | tuple]]):
                Text blocks, each of which consists of lines, each of
                which in turn consists of a left and right part.
                Possible formats:

                  - The blocks can be a multiline string, with empty
                    lines separating the individual blocks; or a list.

                  - In case of list blocks, each block can in turn
                    constitute a multiline string, or a list of lines.

                  - In case of a list block, each line can in turn
                    constitute a string, or a two-element string tuple.

                  - Lines represented by a string are split into a left
                    and right part at the first tab character ('\t').

            **kwargs: Location and formatting options passed to
                ``FlexAxesTextBox.text_blocks``.
        """

        if isinstance(blocks, str):
            # Whole blocks is a multiline string
            blocks = blocks.strip().split('\n\n')

        # Handle case where a multiblock string is embedded
        # in a blocks list alongside string or list blocks
        blocks_orig, blocks = blocks, []
        for block in blocks_orig:
            if isinstance(block, str):
                # Possible multiblock string (if with empty line)
                for subblock in block.strip().split('\n\n'):
                    blocks.append(subblock)
            else:
                # List block
                blocks.append(block)

        # Separate left and right parts of lines
        blocks_l, blocks_r = [], []
        for block in blocks:

            if isinstance(block, str):
                # Turn multiline block into list block
                block = block.strip().split('\n')

            blocks_l.append([])
            blocks_r.append([])
            for line in block:

                # Obtain left and right part of line
                if isinstance(line, str):
                    str_l, str_r = line.split('\t', 1)
                elif len(line) == 2:
                    str_l, str_r = line
                else:
                    raise ValueError(f"invalid line: {line}")

                blocks_l[-1].append(str_l)
                blocks_r[-1].append(str_r)

        dx_l = kwargs.pop('dx', None)
        dx_r = None if dx_l is None else -dx_l

        # Add lines to box
        self.text_blocks('bl', blocks_l, dx=dx_l, **kwargs)
        self.text_blocks('br', blocks_r, dx=dx_r, **kwargs)

    def add_sample_labels(self):
        """Add sample text labels in corners etc."""
        kwargs = dict(fontsize=9)
        self.text('bl', 'bot. left', **kwargs)
        self.text('bc', 'bot. center', **kwargs)
        self.text('br', 'bot. right', **kwargs)
        self.text('cl', 'center left', **kwargs)
        self.text('cc', 'center', **kwargs)
        self.text('cr', 'center right', **kwargs)
        self.text('tl', 'top left', **kwargs)
        self.text('tc', 'top center', **kwargs)
        self.text('tr', 'top right', **kwargs)

    def show_baseline(self, val=True, **kwargs):
        """Show the base line of a text command (for debugging).

        Args:
            val (bool, optional): Whether to show or hide the baseline.
                Defaults to True.

            **kwargs: Keyword arguments passed to ax.axhline().

        """
        self._show_baseline = val
        self._baseline_kwargs = self._baseline_kwargs_default
        self._baseline_kwargs.update(kwargs)


class BoxLocation:
    """Represents reference location inside a box on a 3x3 grid."""

    def __init__(self, loc):
        """Initialize an instance of BoxLocation.

        Args:
            loc (int|str): Location parameter. Takes one of three
                formats: integer, short string, or long string.

                Choices:

                    int     short   long
                    00      bl      bottom left
                    01      bc      bottom center
                    02      br      bottom right
                    10      cl      center left
                    11      cc      center
                    12      cr      center right
                    20      tl      top left
                    21      tc      top center
                    22      tr      top right

        """
        self.loc = loc
        self.loc_y, self.loc_x = self._prepare_loc()

    def _prepare_loc(self):
        """Split and evaluate components of location parameter."""

        loc = str(self.loc)

        # Split location into vertical and horizontal part
        if len(loc) == 2:
            loc_y, loc_x = loc
        elif loc == 'center':
            loc_y, loc_x = loc, loc
        else:
            loc_y, loc_x = line.split(' ', 1)

        # Evaluate location components
        loc_y = self._eval_loc_vert(loc_y)
        loc_x = self._eval_loc_horz(loc_x)

        return loc_y, loc_x

    def _eval_loc_vert(self, loc):
        """Evaluate vertical location component."""
        if loc in (0, '0', 'b', 'bottom'):
            return 'b'
        elif loc in (1, '1', 'c', 'center'):
            return 'c'
        elif loc in (2, '2', 't', 'top'):
            return 't'
        raise ValueError(f"invalid vertical location component '{loc}'")

    def _eval_loc_horz(self, loc):
        """Evaluate horizontal location component."""
        if loc in (0, '0', 'l', 'left'):
            return 'l'
        elif loc in (1, '1', 'c', 'center'):
            return 'c'
        elif loc in (2, '2', 'r', 'right'):
            return 'r'
        raise ValueError(f"invalid horizontal location component '{loc}'")

    def get_va(self):
        """Derive the vertical alignment variable."""
        return {
            'b': 'baseline',
            'c': 'center_baseline',
            #'t': 'top_baseline',  # unfortunately nonexistent
            't': 'top',
        }[self.loc_y]

    def get_ha(self):
        """Derive the horizontal alignment variable."""
        return {
            'l': 'left',
            'c': 'center',
            'r': 'right',
        }[self.loc_x]

    def get_y0(self, dy):
        """Derive the vertical baseline variable."""
        return {
            'b': 0.0 + dy,
            'c': 0.5,
            't': 1.0 - dy,
        }[self.loc_y]

    def get_x0(self, dx):
        """Derive the horizontal baseline variable."""
        return {
            'l': 0.0 + dx,
            'c': 0.5,
            'r': 1.0 - dx,
        }[self.loc_x]


def ax_dims_fig_coords(fig, ax):
    """Get the dimensions of an axes in figure coords."""
    trans = fig.transFigure.inverted()
    x, y, w, h = ax.bbox.transformed(trans).bounds
    return w, h