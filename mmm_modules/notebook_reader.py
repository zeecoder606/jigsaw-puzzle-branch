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
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Pango
import os
#from abiword import Canvas

from gettext import gettext as _
import locale
import logging

logger = logging.getLogger('notebook-reader')

class ReaderProvider (object):
    def __init__ (self, path, lang_details=None):
        self.lang_details = lang_details
        self.path = path
        self.sync()

    def sync (self):
        """ must be called after language changes """
        self.lesson_array = []
        lessons = filter(lambda x: os.path.isdir(os.path.join(self.path, x)), os.listdir(self.path))
        lessons.sort()
        for lesson in lessons:
            if lesson[0].isdigit():
                name = _(lesson[1:])
            else:
                name = _(lesson)
            self.lesson_array.append((name, self._get_lesson_filename(os.path.join(self.path, lesson))))

    def _get_lesson_filename (self, path):
        if self.lang_details:
            code = self.lang_details.code
        else:
            code, encoding = locale.getdefaultlocale()
        if code is None:
            code = 'en'
        files = map(lambda x: os.path.join(path, '%s.abw' % x),
                    ('_'+code.lower(), '_'+code.split('_')[0].lower(), 'default'))
        files = filter(lambda x: os.path.exists(x), files)
        return os.path.join(os.getcwd(), files[0])

    def get_lessons (self):
        """ Returns a list of (name, filename) """
        for name, path in self.lesson_array:
            yield (name, path)

class BasicReaderWidget (Gtk.HBox):
    def __init__ (self, path, lang_details=None):
        super(BasicReaderWidget, self).__init__()
        self.provider = ReaderProvider(path, lang_details)
        return
        #self._canvas = Canvas()
        #self._canvas.show()
        #self.pack_start(self._canvas, True, True, 0)
        #self._canvas.connect_after('map-event', self._map_event_cb)
        
    def get_lessons(self):
        return self.provider.get_lessons()

    def load_lesson (self, path):
        logger.debug("load")
        try:
            self._canvas.load_file('file://'+path, '')
        except:
            self._canvas.load_file(path)
        self._canvas.zoom_whole()
        self._canvas.zoom_width()
        
    def _load_lesson (self, name, path):
        self.load_lesson(path)

    def _map_event_cb(self, o, e):
        self._load_lesson(*self.provider.lesson_array[0])



class NotebookReaderWidget (Gtk.Notebook):
    def __init__ (self, path, lang_details=None):
        super(NotebookReaderWidget, self).__init__()
        self.provider = ReaderProvider(path, lang_details)
        self.set_scrollable(True)
        return
        for name, path in self.provider.get_lessons():
            canvas = Canvas()
            canvas.connect_after('map-event', self._map_event_cb, path)
            canvas.show()
            canvas._mapped = False
            try:
                canvas.load_file('file://' + path, '')
            except:
                canvas.load_file(path)
            self.append_page(canvas, Gtk.Label(label=name))

    def _map_event_cb(self, o, e, path):
        logger.debug("map-event: %s" % path)
        if not o._mapped:
            o.zoom_whole()
            o.zoom_width()
            o._mapped = True
