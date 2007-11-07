#!/usr/bin/env python

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


### notebook_reader.py
### TODO: Describe
### $Id: $
###
### author: Carlos Neves (cn (at) sueste.net)
### (c) 2007 World Wide Workshop Foundation

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango

import os
from abiword import Canvas

from gettext import gettext as _
import locale

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
        canvas = Canvas()
        canvas.show()
        files = map(lambda x: os.path.join(path, '%s.abw' % x),
                    ('_'+code.lower(), '_'+code.split('_')[0].lower(), 'default'))
        files = filter(lambda x: os.path.exists(x), files)
        return os.path.join(os.getcwd(), files[0])

    def get_lessons (self):
        """ Returns a list of (name, filename) """
        for name, path in self.lesson_array:
            yield (name, path)

class BasicReaderWidget (gtk.HBox):
    def __init__ (self, path, lang_details=None):
        super(BasicReaderWidget, self).__init__()
        self._canvas = None
        self.provider = ReaderProvider(path, lang_details)
        self._load_lesson(*self.provider.lesson_array[0])

    def get_lessons(self):
        return self.provider.get_lessons()

    def load_lesson (self, path):
        print "load_lesson:" + path
        if self._canvas:
            self._canvas.hide()
            #self.remove(self._canvas)
            #self._canvas.hide()
            #del self._canvas
        #if not self._canvas:
	canvas = Canvas()
  	canvas.show()
        print "show"
        self.pack_start(canvas)
        print "pack"
        try:
            canvas.load_file('file://'+path, '')
        except:
            canvas.load_file(path)
        print "load"
        #canvas.view_online_layout()
        #canvas.zoom_width()
        #canvas.set_show_margin(False)
        #while gtk.events_pending():
        #    gtk.main_iteration(False)
        if self._canvas:
            #self.remove(self._canvas)
            #self._canvas.unparent()
            del self._canvas
        self._canvas = canvas
    def _load_lesson (self, name, path):
        self.load_lesson(path)

class NotebookReaderWidget (gtk.Notebook):
    def __init__ (self, path, lang_details=None):
        super(NotebookReaderWidget, self).__init__()
        self.provider = ReaderProvider(path, lang_details)
        self.set_scrollable(True)
        for name, path in self.provider.get_lessons():
            self._load_lesson(name, path)

    def _load_lesson (self, name, path):
        canvas = Canvas()
        canvas.show()
        try:
            canvas.load_file(path, 'text/plain')
        except:
            canvas.load_file(path)
        canvas.view_online_layout()
        canvas.zoom_width()
        canvas.set_show_margin(False)
        self.append_page(canvas, gtk.Label(name))
