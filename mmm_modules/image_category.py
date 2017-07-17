# Copyright 2007 World Wide Workshop Foundation
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# If you find this activity useful or end up using parts of it in one of your
# own creations we would love to hear from you at info@WorldWideWorkshop.org !
#

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GObject
import os
from glob import glob
import logging
import md5
from sugar3.activity.activity import Activity, get_bundle_path
from utils import load_image, resize_image, RESIZE_CUT
from borderframe import BorderFrame
from gettext import gettext as _

THUMB_SIZE = 48
IMAGE_SIZE = 200
#MYOWNPIC_FOLDER = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.MyOwnPictures")


def prepare_btn(btn):
    return btn


class ImageSelectorWidget (Gtk.Table):

    def __init__(self, parent,
                 width=IMAGE_SIZE,
                 height=IMAGE_SIZE,
                 frame_color=None,
                 prepare_btn_cb=prepare_btn,
                 method=RESIZE_CUT,
                 image_dir=None):
        Gtk.Table.__init__(self, 2, 5, False)
        self._signals = []
        self.parentp = parent
        self.width = width
        self.height = height
        self.image = Gtk.Image()
        self.method = method
        img_box = BorderFrame()
        img_box.add(self.image)
        img_box.set_border_width(5)

        self.attach(img_box, 0, 5, 0, 1, 0, 0)
        self.attach(Gtk.Label(), 0, 1, 1, 2)
        self.filename = None
        self.show_all()
        self.image.set_size_request(width, height)
