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
"""Plot the 2d image."""

import os

import numpy as np
from chaco.api import ArrayPlotData, Plot, jet
from chaco.tools.api import LineSegmentTool, PanTool, ZoomTool
from chaco.tools.image_inspector_tool import (  # noqa: E501
    ImageInspectorOverlay,
    ImageInspectorTool,
)

# Chaco imports
from enable.api import Component, ComponentEditor, KeySpec
from kiva.agg import points_in_polygon
from pyface.api import ImageResource

# Enthought library imports
from traits.api import (
    Any,
    Bool,
    Button,
    DelegatesTo,
    Enum,
    File,
    Float,
    HasTraits,
    Instance,
    Int,
    Str,
)
from traitsui.api import (
    Action,
    ArrayEditor,
    Group,
    Handler,
    HGroup,
    Item,
    RangeEditor,
    VGroup,
    View,
    spring,
)
from traitsui.menu import CancelButton, OKButton


class SaveLoadMaskHandler(Handler):

    def _save(self, info):
        """Save mask."""
        info.object.saveMaskFile()
        info.ui.dispose()
        return

    def _load(self, info):
        """Load mask."""
        info.object.loadMaskFile()
        info.ui.dispose()
        return


class AdvMaskHandler(Handler):

    def _applyDymask(self, info):
        info.object.refreshMask(staticmask=info.object.staticmask)
        return

    def closed(self, info, is_ok):
        info.object.refreshMask(staticmask=info.object.staticmask)
        return


class ImagePlot(HasTraits):
    imagefile = File
    srx = Any
    srxconfig = Any
    plot = Instance(Component)
    maskfile = File
    pointmaskradius = Float(3.0)
    maskediting = Bool(False)

    brightpixelmask = DelegatesTo(
        "srxconfig",
        desc="Mask the pixels too bright compared to their local environment",
    )
    darkpixelmask = DelegatesTo(
        "srxconfig",
        desc="Mask the pixels too dark compared to their local environment",
    )
    avgmask = DelegatesTo(
        "srxconfig",
        desc=(
            "Mask the pixels too bright or too dark compared to"
            " the average intensity at the similar diffraction angle"
        ),
    )
    brightpixelr = DelegatesTo(
        "srxconfig",
        desc=(
            "Pixels with intensity large than this relative threshold"
            " (times the local environment) value will be masked"
        ),
    )
    brightpixelsize = DelegatesTo(
        "srxconfig",
        desc="Size of testing area for detecting bright pixels",
    )
    darkpixelr = DelegatesTo(
        "srxconfig",
        desc=(
            "Pixels with intensity less than this relative threshold"
            " (times the local environment) value will be masked"
        ),
    )
    avgmaskhigh = DelegatesTo(
        "srxconfig",
        desc=(
            "Comparing to the average intensity at "
            "similar diffraction angle, \npixels with intensity larger than"
            " avg_int*high will be masked"
        ),
    )
    avgmasklow = DelegatesTo(
        "srxconfig",
        desc=(
            "Comparing to the average intensity at "
            "similar diffraction angle, \npixels with intensity less than "
            "avg_int*low will be masked"
        ),
    )
    cropedges = DelegatesTo(
        "srxconfig",
        desc=(
            "The number of pixels masked"
            " at each edge (left, right, top, bottom)"
        ),
    )

    def createPlot(self):
        # image = np.log(
        #     self.srx.loadimage.loadImage(self.imagefile)
        # )

        image = self.srx.loadimage.loadImage(self.imagefile)
        self.maskfile = self.srxconfig.maskfile
        self.imageorg = image
        self.imageorglog = np.log(image)
        self.imageorglog[self.imageorglog < 0] = 0
        self.imageorgmax = image.max()
        self.imageorglogmax = self.imageorglog.max()
        # self.staticmask = self.srx.mask.staticMask()
        # self.dynamicmask = self.genAdvMask(self.imageorg)
        # self.mask = np.logical_or(self.staticmask, self.dynamicmask)
        self.refreshMask(draw=False)

        if self.mask.shape != image.shape:
            self.maskfile = ""
            self.srxconfig.maskfile = ""
            self.srxconfig.ydimension = image.shape[0]
            self.srxconfig.xdimension = image.shape[1]
            # self.mask = self.srx.mask.staticMask()
            self.refreshMask(draw=False)

        y = np.arange(image.shape[0]).reshape((image.shape[0], 1)) * np.ones(
            (1, image.shape[1])
        )
        x = np.arange(image.shape[1]).reshape((1, image.shape[1])) * np.ones(
            (image.shape[0], 1)
        )
        self.pts = np.array(np.vstack([x.ravel(), y.ravel()]).T)
        xbounds = (0, image.shape[1])
        ybounds = (0, image.shape[0])

        self.pd = ArrayPlotData()
        self.refreshImage(mask=self.mask, draw=False)

        self.plot = Plot(self.pd)
        self.img_plot = self.plot.img_plot(
            "imagedata",
            xbounds=xbounds,
            ybounds=ybounds,
            colormap=jet,
        )[0]
        # Tweak some of the plot properties
        self.plot.title = os.path.split(self.imagefile)[1]
        self.plot.aspect_ratio = float(image.shape[1]) / float(image.shape[0])
        self.plot.padding = 50

        # Attach some tools to the plot
        self._appendTools()
        return

    def saveMaskFile(self):
        np.save(self.maskfile, self.staticmask)
        self.srxconfig.maskfile = self.maskfile
        return

    def loadMaskFile(self):
        if self.srxconfig.maskfile == self.maskfile:
            self.refreshMask()
        else:
            self.srxconfig.maskfile = self.maskfile
        return

    def refreshMaskFile(self):
        self.maskfile = self.srxconfig.maskfile
        self.refreshMask()
        return

    def mergeMask(self, points, remove=None):
        """Param points -- an Mx2 array of x,y point pairs (floating
        point) that define the boundaries of a polygon.

        param remove -- True for remove the new mask from the existing
        mask
        """
        if remove is None:
            remove = self.removepolygonmask
        if len(points) > 2:
            mask = points_in_polygon(self.pts, points)
            mask = mask.reshape(self.staticmask.shape)
            if remove:
                self.staticmask = np.logical_and(
                    self.staticmask, np.logical_not(mask)
                )
            else:
                self.staticmask = np.logical_or(self.staticmask, mask)
            self.refreshMask(staticmask=self.staticmask)
        return

    def addPointMask(self, ndx, remove=None):
        """Param ndx -- (x,y) float."""
        x, y = ndx
        r = self.pts - np.array((x, y))
        r = np.sum(r**2, axis=1)
        mask = r < ((self.pointmaskradius + 1) ** 2)
        mask = mask.reshape(self.staticmask.shape)
        if remove:
            self.staticmask = np.logical_and(
                self.staticmask, np.logical_not(mask)
            )
        else:
            self.staticmask = np.logical_or(self.staticmask, mask)
        self.refreshMask(self.staticmask)
        return

    def clearMask(self):
        self.staticmask = self.staticmask * 0
        self.refreshMask(self.staticmask)
        return

    def invertMask(self):
        self.staticmask = np.logical_not(self.staticmask)
        self.refreshMask(self.staticmask)
        return

    def refreshMask(self, staticmask=None, draw=True):
        self.staticmask = (
            self.srx.mask.staticMask() if staticmask is None else staticmask
        )
        self.dynamicmask = self.srx.mask.dynamicMask(
            self.imageorg, dymask=self.staticmask
        )
        self.dynamicmask = np.logical_or(
            self.dynamicmask, self.srx.mask.edgeMask()
        )
        self.mask = np.logical_or(self.staticmask, self.dynamicmask)
        if draw:
            self.refreshImage()
        return

    maskaboveint = Int(10e10)
    maskbelowint = Int(1)

    def maskabove(self):
        mask = self.imageorg > self.maskaboveint
        self.staticmask = np.logical_or(self.staticmask, mask)
        self.refreshMask(self.staticmask)
        return

    def maskbelow(self):
        mask = self.imageorg < self.maskbelowint
        self.staticmask = np.logical_or(self.staticmask, mask)
        self.refreshMask(self.staticmask)
        return

    def _appendTools(self):
        """Append xy position, zoom, pan tools to plot.

        :param plot: the plot object to append on
        """
        plot = self.plot
        img_plot = self.img_plot

        # tools
        self.pan = PanTool(plot)
        self.zoom = ZoomTool(component=plot, tool_mode="box", always_on=False)
        self.lstool = MasklineDrawer(self.plot, imageplot=self)
        self.xyseltool = MaskPointInspector(img_plot, imageplot=self)
        # self.lstool.imageplot = self

        img_plot.tools.append(self.xyseltool)
        overlay = ImageInspectorOverlay(
            component=img_plot,
            image_inspector=self.xyseltool,
            bgcolor="white",
            border_visible=True,
        )
        img_plot.overlays.append(overlay)

        plot.tools.append(self.pan)
        plot.overlays.append(self.zoom)
        return

    def _enableMaskEditing(self):
        """Enable mask tool and disable pan tool."""
        self.maskediting = True
        for i in range(self.plot.tools.count(self.pan)):
            self.plot.tools.remove(self.pan)
        self.plot.overlays.append(self.lstool)
        self.titlebak = self.plot.title
        self.plot.title = (
            "Click: add a vertex; "
            "<Ctrl>+Click: remove a vertex; \n          "
            "<Enter>: finish the selection"
        )
        return

    def _disableMaskEditing(self):
        """Disable mask tool and enable pan tool."""
        self.plot.overlays.remove(self.lstool)
        self.plot.tools.append(self.pan)
        self.plot.title = self.titlebak
        self.maskediting = False
        return

    def _enablePointMaskEditing(self):
        self.maskediting = True
        for i in range(self.plot.tools.count(self.pan)):
            self.plot.tools.remove(self.pan)
        self.titlebak = self.plot.title
        self.plot.title = (
            "Click: add a point; <Enter>: exit the point selection"
        )
        return

    def _disablePointMaskEditing(self):
        self.plot.tools.append(self.pan)
        self.plot.title = self.titlebak
        self.maskediting = False
        return

    def refreshImage(self, mask=None, draw=True):
        """Recalculate the image using self.mask or mask and refresh
        display."""
        mask = self.mask if mask is None else mask
        image = self.applyScale()
        image = image * np.logical_not(mask) + image.max() * mask
        self.pd.set_data("imagedata", image)
        if draw:
            self.plot.invalidate_draw()
        return

    scalemode = Enum("linear", ["linear", "log"], desc="Scale the image")
    scalepowder = Float(0.5, desc="gamma value to control the contrast")

    def applyScale(self, image=None):
        """Apply the scale to increase/decrease contrast."""
        if self.scalemode == "linear":
            if image is None:
                image = self.imageorg
                intmax = self.imageorgmax
            else:
                image = image
                intmax = image.max()
        elif self.scalemode == "log":
            if image is None:
                image = self.imageorglog
                intmax = self.imageorglogmax
            else:
                image = np.log(image)
                image[image < 0] = 0
                intmax = image.max()
        else:
            image = image
            intmax = image.max()

        image = intmax * ((image / intmax) ** self.scalepowder)
        return image

    splb = Float(0.0)
    spub = Float(1.0)

    def _scalemode_changed(self):
        if self.scalemode == "linear":
            self.scalepowder = 0.5
            self.splb = 0.0
            self.spub = 1.0
        elif self.scalemode == "log":
            self.scalepowder = 1.0
            self.splb = 0.0
            self.spub = 4.0
        self.refreshImage()
        return

    def _scalepowder_changed(self, old, new):
        if np.round(old, 1) != np.round(new, 1):
            self.refreshImage()
        return

    def _add_notifications(self):
        self.on_trait_change(self.refreshMaskFile, "srxconfig.maskfile")
        return

    def _del_notifications(self):
        self.on_trait_change(
            self.refreshMaskFile, "srxconfig.maskfile", remove=True
        )
        return

    addpolygon_bb = Button("Add polygon mask")
    removepolygon_bb = Button("Remove polygon mask")
    addpoint_bb = Button("Add point mask")
    clearmask_bb = Button("Clear mask", desc="Clear mask")
    invertmask_bb = Button("Invert mask", desc="Invert mask")
    advancedmask_bb = Button(
        "Dynamic mask",
        desc="The dynamic mask is dynamically generated for each image.",
    )
    maskabove_bb = Button("Mask intensity above")
    maskbelow_bb = Button("Mask intensity below")
    loadmaskfile_bb = Button("Load mask")
    savemaskfile_bb = Button("Save mask")

    def _addpolygon_bb_fired(self):
        self.removepolygonmask = False
        self._enableMaskEditing()
        return

    def _removepolygon_bb_fired(self):
        self.removepolygonmask = True
        self._enableMaskEditing()
        return

    def _addpoint_bb_fired(self):
        self._enablePointMaskEditing()
        self.xyseltool.enablemaskselect = True
        return

    def _clearmask_bb_fired(self):
        self.clearMask()
        return

    def _invertmask_bb_fired(self):
        self.invertMask()
        return

    def _advancedmask_bb_fired(self):
        self.edit_traits("advancedmask_view")
        # if not hasattr(self, 'advhint'):
        #    self.advhint = AdvHint()
        #   self.advhint.edit_traits('advhint_view')
        return

    def _maskabove_bb_fired(self):
        self.maskabove()
        return

    def _maskbelow_bb_fired(self):
        self.maskbelow()
        return

    def _loadmaskfile_bb_fired(self):
        self.edit_traits("loadmaskfile_view")
        return

    def _savemaskfile_bb_fired(self):
        if self.maskfile == "":
            self.maskfile = os.path.join(
                self.srxconfig.savedirectory, "mask.npy"
            )
        else:
            self.maskfile = os.path.splitext(self.maskfile)[0] + ".npy"
        self.edit_traits("savemaskfile_view")
        return

    def __init__(self, **kwargs):
        """Init the object and create notification."""
        HasTraits.__init__(self, **kwargs)
        self.createPlot()
        # self._loadMaskPar()
        self._add_notifications()
        return

    hinttext = Str(
        "Zoom: <z>;  Reset: <Esc>;"
        " Pan: <drag/drop>; Toggle XY coordinates: <P>"
    )
    traits_view = View(
        Group(
            Item(
                "plot",
                editor=ComponentEditor(size=(550, 550)),
                show_label=False,
            ),
            HGroup(
                spring,
                Item("scalemode", label="Scale mode"),
                Item(
                    "scalepowder",
                    label="Gamma",
                    editor=RangeEditor(
                        auto_set=False,
                        low_name="splb",
                        high_name="spub",
                        format="%.1f",
                    ),
                ),
                spring,
            ),
            VGroup(
                HGroup(
                    Item("addpolygon_bb", enabled_when="not maskediting"),
                    Item(
                        "removepolygon_bb",
                        enabled_when="not maskediting",
                    ),
                    spring,
                    Item("maskabove_bb", enabled_when="not maskediting"),
                    Item("maskaboveint", enabled_when="not maskediting"),
                    show_labels=False,
                ),
                HGroup(
                    Item("addpoint_bb", enabled_when="not maskediting"),
                    Item(
                        "pointmaskradius",
                        label="Size:",
                        show_label=True,
                    ),
                    spring,
                    Item("maskbelow_bb", enabled_when="not maskediting"),
                    Item("maskbelowint", enabled_when="not maskediting"),
                    show_labels=False,
                ),
                HGroup(
                    Item("clearmask_bb", enabled_when="not maskediting"),
                    Item("invertmask_bb", enabled_when="not maskediting"),
                    Item(
                        "advancedmask_bb",
                        enabled_when="not maskediting",
                    ),
                    spring,
                    Item("loadmaskfile_bb"),
                    Item("savemaskfile_bb"),
                    show_labels=False,
                ),
                show_labels=False,
                show_border=True,
                label="Mask",
            ),
            orientation="vertical",
        ),
        resizable=True,
        title="2D image",
        statusbar=["hinttext"],
        width=600,
        height=700,
        icon=ImageResource("icon.png"),
    )

    savemaskfile_action = Action(name="OK ", action="_save")
    loadmaskfile_action = Action(name="OK ", action="_load")
    applydymask_action = Action(name="Apply ", action="_applyDymask")

    savemaskfile_view = View(
        Item("maskfile"),
        buttons=[savemaskfile_action, CancelButton],
        title="Save mask file",
        width=500,
        resizable=True,
        handler=SaveLoadMaskHandler(),
        icon=ImageResource("icon.png"),
    )

    loadmaskfile_view = View(
        Item("maskfile"),
        buttons=[loadmaskfile_action, CancelButton],
        title="Load mask file",
        width=500,
        resizable=True,
        handler=SaveLoadMaskHandler(),
        icon=ImageResource("icon.png"),
    )

    advancedmask_view = View(
        Group(
            VGroup(
                Item(
                    "cropedges",
                    label="Mask edges",
                    editor=ArrayEditor(width=-50),
                ),
                label="Edge mask",
                show_border=True,
            ),
            VGroup(
                Item("darkpixelmask", label="Enable"),
                Item(
                    "darkpixelr",
                    label="Threshold",
                    enabled_when="darkpixelmask",
                ),
                label="Dark pixel mask",
                show_border=True,
            ),
            VGroup(
                Item("brightpixelmask", label="Enable"),
                Item(
                    "brightpixelsize",
                    label="Testing size",
                    enabled_when="brightpixelmask",
                ),
                Item(
                    "brightpixelr",
                    label="Threshold",
                    enabled_when="brightpixelmask",
                ),
                label="Bright pixel mask",
                show_border=True,
            ),
            VGroup(
                Item("avgmask", label="Enable"),
                Item("avgmaskhigh", label="High", enabled_when="avgmask"),
                Item("avgmasklow", label="Low", enabled_when="avgmask"),
                label="Average mask",
                show_border=True,
            ),
        ),
        title="Dynamic mask",
        width=320,
        handler=AdvMaskHandler(),
        resizable=True,
        buttons=[applydymask_action, OKButton, CancelButton],
        icon=ImageResource("icon.png"),
    )


class MasklineDrawer(LineSegmentTool):
    """"""

    imageplot = Any

    def _finalize_selection(self):
        self.imageplot._disableMaskEditing()
        self.imageplot.mergeMask(self.points)
        return

    def __init__(self, *args, **kwargs):
        LineSegmentTool.__init__(self, *args, **kwargs)
        self.line.line_color = "red"
        self.line.vertex_color = "white"
        return


class MaskPointInspector(ImageInspectorTool):
    exitmask_key = KeySpec("Enter")
    imageplot = Any
    enablemaskselect = Bool(False)

    def normal_key_pressed(self, event):
        if self.inspector_key.match(event):
            self.visible = not self.visible
            event.handled = True
        if self.exitmask_key.match(event):
            self.enablemaskselect = False
            self.imageplot._disablePointMaskEditing()
        return

    def normal_left_down(self, event):
        if self.enablemaskselect:
            ndx = self.component.map_index((event.x, event.y))
            self.imageplot.addPointMask(ndx)
        return


class AdvHint(HasTraits):
    advhinttext = Str(
        "Notes: Advanced Masks are generated during the integration\n"
        "and refreshed for each image.\n"
        "You can preview the masks here or apply the current masks\n"
        "to the static mask permanently.\n\n"
        "Edge mask: mask the pixels around the image edge.\n"
        "(left, right, top, bottom)\n\n"
        "Dark pixel mask: mask the pixels too dark\n"
        "compared to their local environment\n\n"
        "Bright pixel mask: mask the pixels too bright\n"
        "compared to their local environment\n"
        "Average mask: Mask the pixels too bright or too dark\n"
        "compared to the average intensity at the similar diffraction angle.\n"
        "Correct calibration information is required."
    )

    advhint_view = View(
        Group(
            Item("advhinttext", style="readonly", show_label=False),
            show_border=True,
        ),
        title="Advanced mask hints",
        width=640,
        resizable=False,
        buttons=[OKButton],
        icon=ImageResource("icon.png"),
    )
