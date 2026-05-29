#!/usr/bin/env python
##############################################################################
#
# diffpy.srxplanargui    by Simon J. L. Billinge group
#                   (c) 2012 Trustees of the Columbia University
#                   in the City of New York.  All rights reserved.
#
# File coded by:    Xiaohao Yang
#
# See AUTHORS.rst for a list of people who contributed.
# See LICENSE.rst for license information.
#
##############################################################################


import os

from pyface.api import ImageResource
from traits.api import (
    Any,
    Bool,
    Button,
    Directory,
    Enum,
    Event,
    HasTraits,
    Instance,
    Property,
    Str,
    on_trait_change,
    property_depends_on,
)
from traitsui.api import (
    Group,
    Handler,
    HGroup,
    Item,
    TableEditor,
    TextEditor,
    TitleEditor,
    VGroup,
    View,
    spring,
)
from traitsui.editors.table_editor import TableEditor as TableEditorBE
from traitsui.menu import CancelButton, OKButton
from traitsui.table_column import ObjectColumn

try:
    from diffpy.pdfgetx.functs import sortKeyNumericString
except ImportError:
    from diffpy.pdfgete.functs import sortKeyNumericString

from diffpy.srxplanar.loadimage import openImage, saveImage
from diffpy.srxplanargui.datacontainer import DataContainer
from diffpy.srxplanargui.imageplot import ImagePlot
from diffpy.srxplanargui.srxconfig import SrXconfig

# -- The Live Search table editor definition ------------------------------


class AddFilesHandler(Handler):

    def object_selectallbb_changed(self, info):
        """Select all files."""
        # FIXME
        try:
            editor = [
                aa for aa in info.ui._editors if isinstance(aa, TableEditorBE)
            ][0]
            info.object.selected = [
                info.object.datafiles[i] for i in editor.filtered_indices
            ]
            editor.refresh()
        except (AttributeError, IndexError):
            pass
        return

    def object_dclick_changed(self, info):
        info.object._plotbb_fired()
        return


class SaveImageHandler(Handler):

    def closed(self, info, is_ok):
        if is_ok:
            info.object._sumImgs()
        return


class AddFiles(HasTraits):

    srxconfig = Instance(SrXconfig)

    # The currently inputdir directory being searched:
    # inputdir = DelegatesTo('srxconfig')
    inputdir = Directory()  # , entries = 10 )

    def _inputdir_default(self):
        return self.srxconfig.opendirectory

    # Should sub directories be included in the search:
    recursive = Bool(False)
    # The file types to include in the search:
    filetype = Enum("tif", "npy", "all")
    # The current search string:
    search = Str
    # Is the search case sensitive?
    casesensitive = Bool(False)
    # The live search table filter:
    filter = Property  # Instance( TableFilter )
    # The current list of source files being searched:
    datafiles = Property  # List( string )
    # The currently selected source file:
    selected = Any  # list( DtaContainer)
    dclick = Event
    # Summary of current number of files:
    summary = Property  # Str
    # some meta data
    _filetypedict = {
        "tif": [".tif", ".tiff", ".tif.bz2"],
        "npy": [".npy"],
        "all": "all",
    }

    # -- Property Implementations ---------------------------------------------

    @property_depends_on("search, casesensitive")
    def _get_filter(self):
        """Get filename filter."""
        return _createFileNameFilter(self.search, self.casesensitive)

    refreshdatalist = Event

    @property_depends_on("inputdir, recursive, filetype, refreshdatalist")
    def _get_datafiles(self):
        """Create a datacontainer list, all files under inputdir is
        filtered using filetype."""
        inputdir = self.inputdir
        if inputdir == "":
            inputdir = os.getcwd()
        if not os.path.exists(inputdir):
            self.srxconfig.opendirectory = os.getcwd()
            inputdir = os.getcwd()

        filetypes = self._filetypedict[self.filetype]
        if self.recursive:
            rv = []
            for dirpath, dirnames, filenames in os.walk(inputdir):
                for filename in filenames:
                    if (os.path.splitext(filename)[1] in filetypes) or (
                        filetypes == "all"
                    ):
                        rv.append(os.path.join(dirpath, filename))
        else:
            rv = [
                os.path.join(inputdir, filename)
                for filename in os.listdir(inputdir)
                if (os.path.splitext(filename)[1] in filetypes)
                or (filetypes == "all")
            ]

        rv.sort(key=sortKeyNumericString)
        rvlist = [DataContainer(fullname=fn) for fn in rv]
        return rvlist

    @property_depends_on("datafiles, search, casesensitive, selected")
    def _get_summary(self):
        """Get summary of file."""
        if self.selected and self.datafiles:
            rv = "%d files selected in a total of %d files." % (
                len(self.selected),
                len(self.datafiles),
            )
        else:
            rv = "0 files selected in a total of 0 files."
        return rv

    @on_trait_change("srxconfig.opendirectory")
    def _changeInputdir(self):
        """Change inputdir of getxconfig."""
        self.inputdir = self.srxconfig.opendirectory
        return

    def _plotbb_fired(self):
        try:
            imagefile = self.selected[0].fullname
        except IndexError:
            imagefile = None
        if imagefile is not None:
            if os.path.exists(imagefile):
                imageplot = ImagePlot(
                    imagefile=imagefile,
                    srx=self.srx,
                    srxconfig=self.srxconfig,
                )
                # imageplot.createPlot()
                imageplot.edit_traits()
        return

    def _refreshbb_fired(self):
        self.refreshdatalist = True
        return

    sumname = Str

    def _sumbb_fired(self):
        self.sumname = (
            os.path.splitext(self.selected[0].fullname)[0] + "_sum.tif"
        )
        self.edit_traits(view="saveimage_view")
        return

    def _sumImgs(self):
        if len(self.selected) > 1:
            sel = self.selected
            img = openImage(sel[0].fullname)
            for im in sel[1:]:
                img += openImage(im.fullname)
            img /= len(sel)
            saveImage(self.sumname, img)
            self.refreshdatalist = True
        return

    saveimage_view = View(
        Group(
            Item("sumname", springy=True, label="File name"),
        ),
        buttons=[OKButton, CancelButton],
        title="Save image",
        width=500,
        # height    = 400,
        resizable=True,
        handler=SaveImageHandler(),
        icon=ImageResource("icon.png"),
    )

    # -- Traits UI Views ------------------------------------------------------
    tableeditor = TableEditor(
        columns=[
            ObjectColumn(
                name="basename",
                label="Name",
                # width=0.70,
                editable=False,
            ),
        ],
        auto_size=True,
        # show_toolbar = True,
        deletable=True,
        # reorderable = True,
        edit_on_first_click=False,
        filter_name="filter",
        selection_mode="rows",
        selected="selected",
        dclick="dclick",
        label_bg_color="(244, 243, 238)",
        cell_bg_color="(234, 233, 228)",
    )

    selectallbb = Button("Select all")
    refreshbb = Button("Refresh")
    plotbb = Button("Mask")
    sumbb = Button("Sum")

    traits_view = View(
        VGroup(
            VGroup(
                HGroup(
                    Item(
                        "search",
                        id="search",
                        springy=True,
                        editor=TextEditor(auto_set=False),
                    ),
                ),
                HGroup(
                    spring,
                    Item("selectallbb", show_label=False),
                    Item("refreshbb", show_label=False),
                    spring,
                    Item("filetype", label="Type"),
                ),
                Item("datafiles", id="datafiles", editor=tableeditor),
                Item("summary", editor=TitleEditor()),
                HGroup(
                    spring,
                    Item("plotbb", show_label=False),
                    Item("sumbb", show_label=False),
                    spring,
                ),
                dock="horizontal",
                show_labels=False,
            ),
        ),
        # title     = 'Add files',
        # width     = 500,
        height=600,
        resizable=True,
        handler=AddFilesHandler(),
    )


def _createFileNameFilter(pattern, casesensitive):
    """Build function that returns True for matching files.

    pattern  -- string pattern to be matched
    casesensitive -- flag for case-sensitive file matching

    Return callable object.
    """
    try:
        from diffpy.pdfgetx.multipattern import MultiPattern
    except ImportError:
        from diffpy.pdfgete.multipattern import MultiPattern
    # MultiPattern always matches for an empty pattern, thus there
    # is no need to handle empty search string in a special way.
    patterns = pattern.split()
    if not casesensitive:
        patterns = [p.lower() for p in patterns]

    mp = MultiPattern(patterns)

    def rv(x):
        name = x.basename
        if not casesensitive:
            name = name.lower()
        return mp.match(name)

    return rv


# Run the demo (if invoked from the command line):
if __name__ == "__main__":
    addfiles = AddFiles()
    addfiles.configure_traits()
