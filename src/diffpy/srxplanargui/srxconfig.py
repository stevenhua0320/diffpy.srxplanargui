#!/usr/bin/env python
##############################################################################
#
# diffpy.srxplanar  by DANSE Diffraction group
#                   Simon J. L. Billinge
#                   (c) 2010-2025 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Xiaohao Yang
#
# See AUTHORS.rst for a list of people who contributed.
# See LICENSE.rst for license information.
#
##############################################################################


import os

import numpy as np
from pyface.api import ImageResource
from traits.api import Bool, Enum, Property, on_trait_change
from traits.etsconfig.api import ETSConfig
from traitsui.api import Group, Item, View

from diffpy.srxconfutils.configtraits import ConfigBaseTraits
from diffpy.srxplanar.srxplanarconfig import (
    _description,
    _epilog,
    _optdatalist,
    checkMax,
)

ETSConfig.toolkit = "qt"


_optdatalist.append(
    [
        "xpixelsizetem",
        {
            "sec": "Beamline",
            "h": "detector pixel size in x axis, in A^-1",
            "d": 0.02,
        },
    ]
)
_optdatalist.append(
    [
        "ypixelsizetem",
        {
            "sec": "Beamline",
            "h": "detector pixel size in y axis, in A^-1",
            "d": 0.02,
        },
    ]
)

for i in _optdatalist:
    if i[0] == "polcorrectionenable":
        i[1] = {
            "sec": "Others",
            "args": "n",
            "config": "n",
            "header": "n",
            "s": "polarcorr",
            "h": "enable polarization correction",
            "n": "?",
            "co": False,
            "d": False,
        }
    elif i[0] == "polcorrectf":
        i[1] = {
            "sec": "Others",
            "args": "n",
            "config": "n",
            "header": "n",
            "s": "polarf",
            "h": "polarization correction factor",
            "d": 0.99,
        }
    elif i[0] == "xpixelsize":
        i[1] = {
            "sec": "Beamline",
            "args": "n",
            "config": "n",
            "header": "n",
            "s": "xp",
            "h": "detector pixel size in x axis, in mm",
            "d": 0.2,
        }
    elif i[0] == "ypixelsize":
        i[1] = {
            "sec": "Beamline",
            "args": "n",
            "config": "n",
            "header": "n",
            "s": "yp",
            "h": "detector pixel size in y axis, in mm",
            "d": 0.2,
        }


class SrXconfig(ConfigBaseTraits):
    """Config class, based on ConfigBase class in diffpy.confutils."""

    # Text to display before the argument help
    _description = _description

    # Text to display after the argument help
    _epilog = _epilog

    _optdatalist = _optdatalist

    _defaultdata = {
        "configfile": [],
        "headertitle": "SrXgui configuration",
    }

    rotation = Property(
        depends_on="rotationd",
        fget=lambda self: np.radians(self.rotationd),
    )
    tilt = Property(
        depends_on="tiltd", fget=lambda self: np.radians(self.tiltd)
    )
    tthstep = Property(
        depends_on="tthstepd",
        fget=lambda self: np.radians(self.tthstepd),
    )
    tthmax = Property(
        depends_on="tthmaxd", fget=lambda self: np.radians(self.tthmaxd)
    )

    tthorqmax = Property(
        depends_on="integrationspace, tthmaxd, qmax",
        fget=lambda self: (
            self.tthmax if self.integrationspace == "twotheta" else self.qmax
        ),
    )
    tthorqstep = Property(
        depends_on="integrationspace, tthmaxd, qmax",
        fget=lambda self: (
            self.tthstep if self.integrationspace == "twotheta" else self.qstep
        ),
    )

    def _preUpdateSelf(self, **kwargs):
        """Additional process called in self._updateSelf, this method is
        called before self._copySelftoConfig(), i.e. before copy options
        value to self.config (config file)

        check the tthmaxd and qmax, and set tthorqmax, tthorqstep
        according to integration space

        :param kwargs: optional kwargs
        """
        self.tthmaxd, self.qmax = checkMax(self)
        """Addmask = [b for b in self.addmask if not (b in
        ['brightpixel', 'darkpixel'])] if len(addmask) > 0:

        self.maskfile = addmask[0]
        """
        return

    def _opendirectory_changed(self):
        if os.path.exists(self.opendirectory):
            self.savedirectory = os.path.abspath(self.opendirectory)
        else:
            self.opendirectory = os.path.abspath(os.curdir)
            self.savedirectory = os.path.abspath(os.curdir)
        return

    def _savedirectory_changed(self):
        if not os.path.exists(self.savedirectory):
            self.savedirectory = os.path.abspath(os.curdir)
        return

    configmode = Enum(["TEM", "normal"])

    @on_trait_change("distance, wavelength, xpixelsizetem, ypixelsizetem")
    def _refreshPSsize(self, obj, name, new):
        self.updateConfig(
            xpixelsize=self.xpixelsizetem * self.wavelength * self.distance,
            ypixelsize=self.ypixelsizetem * self.wavelength * self.distance,
        )
        return

    directory_group = Group(
        Item(
            "opendirectory",
            label="Input dir.",
            help="directory of 2D images",
        ),
        Item(
            "savedirectory",
            label="Output dir.",
            help="directory of saved files",
        ),
        show_border=True,
        label="Files",
    )
    mask_group = Group(
        Item("maskfile", label="Mask file"),
        show_border=True,
        label="Masks",
    )

    geometry_visible = Bool(False)
    geometry_group = Group(
        Item("integrationspace", label="Integration grid"),
        Item(
            "wavelength",
            visible_when='integrationspace == "qspace"',
            label="Wavelength",
        ),
        Item("xbeamcenter", label="X beamcenter"),
        Item("ybeamcenter", label="Y beamcenter"),
        Item(
            "distance",
            label="Camera length",
            visible_when='configmode == "TEM"',
        ),
        Item(
            "distance",
            label="Distance",
            visible_when='configmode == "normal"',
        ),
        Item("rotationd", label="Rotation"),
        Item("tiltd", label="Tilt rotation"),
        Item(
            "tthstepd",
            label="Integration step",
            visible_when='integrationspace == "twotheta"',
        ),
        Item(
            "qstep",
            label="Integration step",
            visible_when='integrationspace == "qspace"',
        ),
        show_border=True,
        # label='Geometry parameters',
        visible_when="geometry_visible",
    )

    correction_visible = Bool(False)
    correction_group = Group(
        Item("uncertaintyenable", label="Uncertainty"),
        Item("sacorrectionenable", label="solid angle corr."),
        # Item('polcorrectionenable', label='polarization corr.'),
        # Item('polcorrectf', label='polarization factor'),
        # Item('brightpixelmask', label='Bright pixel mask'),
        # Item('darkpixelmask', label='Dark pixel mask'),
        # Item('avgmask', label='Average mask'),
        # Item('cropedges', label='Crop edges', editor=ArrayEditor(width=-50)),
        show_border=True,
        # label='Corrections'
        visible_when="correction_visible",
    )

    detector_visible = Bool(False)
    detector_group = (
        Group(
            Item("fliphorizontal", label="Flip horizontally"),
            Item("flipvertical", label="Flip vertically"),
            Item("xdimension", label="x dimension"),
            Item("ydimension", label="y dimension"),
            Item(
                "xpixelsizetem",
                label="x pixel size (A^-1)",
                tooltip="x pixel size, in A^-1",
                visible_when='configmode == "TEM"',
            ),
            Item(
                "ypixelsizetem",
                label="y pixel size (A^-1)",
                tooltip="y pixel size, in A^-1",
                visible_when='configmode == "TEM"',
            ),
            show_border=True,
            # label='Detector parameters'
            visible_when="detector_visible",
        ),
    )

    main_view = View(
        Group(
            directory_group,
            mask_group,
            Group(
                # Item('configmode'),
                Group(
                    Item("geometry_visible", label="Geometry parameters"),
                    geometry_group,
                ),
                Group(
                    Item("correction_visible", label="Corrections"),
                    correction_group,
                ),
                Group(
                    Item("detector_visible", label="Detector parameters"),
                    detector_group,
                ),
                # label = 'Basic'
                show_border=True,
            ),
        ),
        resizable=True,
        scrollable=True,
        # handler = handler,
        icon=ImageResource("icon.png"),
    )


SrXconfig.initConfigClass()

if __name__ == "__main__":
    a = SrXconfig()
    # a.updateConfig()
    a.configure_traits(view="main_view")
