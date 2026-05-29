#!/usr/bin/env python
##############################################################################
#
# diffpy.srxplanargui    by Simon J. L. Billinge group
#                   (c) 2012-2025 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Xiaohao Yang
#
# See AUTHORS.rst for a list of people who contributed.
# See LICENSE.rst for license information.
#
##############################################################################
"""Provide help for SrXgui."""

import sys

from pyface.api import ImageResource
from traits.api import HasTraits, Int, Property, property_depends_on
from traits.etsconfig.api import ETSConfig
from traitsui.api import Action, Handler, ImageEditor, Item, View
from traitsui.menu import OKButton


class HelpHandler(Handler):

    def _qsnext(self, info):
        info.object.qsindex += 1
        return

    def _qsprevious(self, info):
        info.object.qsindex -= 1
        return

    def _cpReftext(self, info):
        info.object.cpReftext()
        return


class SrXguiHelp(HasTraits):

    if sys.platform.startswith("win"):
        if ETSConfig.toolkit == "qt":
            hheight = 510
            hwidth = 960
        else:
            hheight = 556
            hwidth = 980
    else:
        hheight = 524
        hwidth = 964

    #######################
    # quick start
    #######################

    imgs = [ImageResource("%02d.png" % i) for i in range(1, 23)]

    qslen = Int(len(imgs) - 1)

    next_action = Action(
        name="Next",
        action="_qsnext",
        enabled_when="object.qsindex<object.qslen",
    )
    previous_action = Action(
        name="Previous",
        action="_qsprevious",
        enabled_when="object.qsindex>0",
    )
    cpreference_action = Action(
        name="Copy to clipboard",
        action="_cpReftext",
        visible_when="object.qsindex==object.qslen-1",
    )

    def _qsnext(self):
        self.qsindex += 1
        return

    def _qsprevious(self):
        self.qsindex -= 1
        return

    qsimage = Property

    @property_depends_on("qsindex")
    def _get_qsimage(self):
        return self.imgs[self.qsindex]

    qsindex = Int(0)
    quickstart_view = View(
        Item("qsimage", editor=ImageEditor(), width=0.5, show_label=False),
        title="Quick start",
        width=hwidth,
        height=hheight,
        resizable=True,
        buttons=[
            cpreference_action,
            previous_action,
            next_action,
            OKButton,
        ],
        handler=HelpHandler(),
        icon=ImageResource("icon.png"),
    )

    #######################
    # reference
    #######################

    reftext = """
xPDFsuite (main GUI) :X. Yang, P. Juhas, C. L. Farrow and Simon J. L. Billinge
xPDFsuite: an end-to-end software solution for high throughput
pair distribution function transformation,
visualization and analysis, arXiv 1402.3163 (2014)

SrXplanar (2D image integration):X. Yang, P. Juhas, S.J.L. Billinge,
On the estimation of statistical uncertainties on powder diffraction
and small-angle scattering data from two-dimensional X-ray detectors,
J. Appl. Cryst. (2014). 47, 1273-1283
"""

    def cpReftext(self):
        cpToClipboard(self.reftext)
        return


def cpToClipboard(s):
    if ETSConfig.toolkit == "qt4":
        from pyface.qt import QtGui

        cb = QtGui.QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText(s, mode=cb.Clipboard)
