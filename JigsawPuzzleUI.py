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


### JigsawPuzzeUI
### TODO: Describe
### $Id: $
###
### author: Carlos Neves (cn (at) sueste.net)
### (c) 2007 World Wide Workshop Foundation

import pygtk
pygtk.require('2.0')
import gtk, gobject, pango
import os

from mamamedia_modules import BorderFrame, BORDER_ALL_BUT_BOTTOM, BORDER_ALL_BUT_LEFT
from mamamedia_modules import utils
from mamamedia_modules import CategorySelector
from mamamedia_modules import ImageSelectorWidget
from mamamedia_modules import LanguageComboBox
from mamamedia_modules import TimerWidget
from mamamedia_modules import NotebookReaderWidget
from JigsawPuzzleWidget import JigsawPuzzleWidget, CutterBasic, CutterSimple, CutterClassic

import logging

from gettext import gettext as _

# Colors from Rich's UI design

COLOR_FRAME_OUTER = "#B7B7B7"
COLOR_FRAME_GAME = "#FF0099"
COLOR_FRAME_THUMB = COLOR_FRAME_GAME
COLOR_FRAME_CONTROLS = "#FFFF00"
COLOR_BG_CONTROLS = "#66CC00"
COLOR_FG_BUTTONS = (
    (gtk.STATE_NORMAL,"#CCFF99"),
    (gtk.STATE_ACTIVE,"#CCFF99"),
    (gtk.STATE_PRELIGHT,"#CCFF99"),
    (gtk.STATE_SELECTED,"#CCFF99"),
    (gtk.STATE_INSENSITIVE,"#CCFF99"),
    )
COLOR_BG_BUTTONS = (
    (gtk.STATE_NORMAL,"#027F01"),
    (gtk.STATE_ACTIVE,"#014D01"),
    (gtk.STATE_PRELIGHT,"#016D01"),
    (gtk.STATE_SELECTED,"#027F01"),
    (gtk.STATE_INSENSITIVE,"#027F01"),
    )

def prepare_btn(btn, w=-1, h=-1):
    for state, color in COLOR_BG_BUTTONS:
        btn.modify_bg(state, gtk.gdk.color_parse(color))
    c = btn.get_child()
    if c is not None:
        for state, color in COLOR_FG_BUTTONS:
            c.modify_fg(state, gtk.gdk.color_parse(color))
    else:
        for state, color in COLOR_FG_BUTTONS:
            btn.modify_fg(state, gtk.gdk.color_parse(color))
    if w>0 or h>0:
        btn.set_size_request(w, h)
    return btn


class JigsawPuzzleUI (BorderFrame):
    
    def __init__(self, parent):
        super(JigsawPuzzleUI, self).__init__(border_color=COLOR_FRAME_OUTER)
        self._parent = parent
        self.labels_to_translate = []

        inner_table = gtk.Table(2,2,False)
        self.add(inner_table)

        self.game = JigsawPuzzleWidget()
        self.game.connect('picked', self.piece_pick_cb)
        self.game.connect('solved', self.do_solve)
        self.game.show()

        # panel is a holder for everything on the left side down to (not inclusive) the language dropdown
        panel = gtk.VBox()

        # Logo image
        img_logo = gtk.Image()
        img_logo.set_from_file("icons/logo.png")
        img_logo.show()
        panel.pack_start(img_logo, expand=False, fill=False)


        # Control panel has the image controls
        control_panel = BorderFrame(border=BORDER_ALL_BUT_BOTTOM,
                                    border_color=COLOR_FRAME_CONTROLS,
                                    bg_color=COLOR_BG_CONTROLS)
        control_panel_box = gtk.VBox()
        control_panel.add(control_panel_box)

        spacer = gtk.Label()
        spacer.set_size_request(-1, 5)
        control_panel_box.pack_start(spacer, expand=False, fill=False)

        btn_box = gtk.Table(2,5,False)
        btn_box.set_col_spacings(5)
        btn_box.set_row_spacings(5)
        btn_box.attach(gtk.Label(), 0,1,0,2)
        # Cut type buttons
        self.btn_basic_cut = gtk.ToggleButton()
        i = gtk.Image()
        i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'cut_basic.svg')))
        self.btn_basic_cut.connect("clicked", self.set_piece_cut, CutterBasic)
        self.btn_basic_cut.set_image(i)
        btn_box.attach(prepare_btn(self.btn_basic_cut), 1,2,0,1,0,0)
        self.btn_simple_cut = gtk.ToggleButton()
        i = gtk.Image()
        i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'cut_simple.svg')))
        self.btn_simple_cut.connect("clicked", self.set_piece_cut, CutterSimple)
        self.btn_simple_cut.set_image(i)
        btn_box.attach(prepare_btn(self.btn_simple_cut), 2,3,0,1,0,0)
        self.btn_classic_cut = gtk.ToggleButton()
        i = gtk.Image()
        i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'cut_classic.svg')))
        self.btn_classic_cut.set_active(True)
        self.btn_classic_cut.connect("clicked", self.set_piece_cut, CutterClassic)
        self.btn_classic_cut.set_image(i)
        btn_box.attach(prepare_btn(self.btn_classic_cut), 3,4,0,1,0,0)
        # Difficulty level buttons
        self.btn_easy_level = gtk.ToggleButton()
        i = gtk.Image()
        i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'level_easy.svg')))
        self.btn_easy_level.set_active(True)
        self.btn_easy_level.connect("clicked", self.set_level, 0)
        self.btn_easy_level.set_image(i)
        btn_box.attach(prepare_btn(self.btn_easy_level), 1,2,1,2,0,0)
        self.btn_normal_level = gtk.ToggleButton()
        i = gtk.Image()
        i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'level_normal.svg')))
        self.btn_normal_level.connect("clicked", self.set_level, 1)
        self.btn_normal_level.set_image(i)
        btn_box.attach(prepare_btn(self.btn_normal_level), 2,3,1,2,0,0)
        self.btn_hard_level = gtk.ToggleButton()
        i = gtk.Image()
        i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'level_hard.svg')))
        self.btn_hard_level.connect("clicked", self.set_level, 2)
        self.btn_hard_level.set_image(i)
        btn_box.attach(prepare_btn(self.btn_hard_level), 3,4,1,2,0,0)

        btn_box.attach(gtk.Label(), 4,5,0,2)
        control_panel_box.pack_start(btn_box, expand=False)

        self.thumb = ImageSelectorWidget(frame_color=COLOR_FRAME_THUMB, prepare_btn_cb=prepare_btn, method=utils.RESIZE_PAD)
        self.thumb.connect("category_press", self.do_select_category)
        self.thumb.connect("image_press", self.do_shuffle)
        control_panel_box.pack_start(self.thumb, expand=False)

        spacer = gtk.Label()
        spacer.set_size_request(-1, 5)
        control_panel_box.pack_start(spacer, expand=False, fill=False)
        
        # The game control buttons
        btn_box = gtk.Table(3,4,False)
        btn_box.set_row_spacings(2)
        btn_box.attach(gtk.Label(), 0,1,0,4)
        btn_box.attach(gtk.Label(), 2,3,0,4)
        self.btn_solve = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append([self.btn_solve, _("Solve")])
        self.btn_solve.connect("clicked", self.do_solve)
        btn_box.attach(self.btn_solve, 1,2,0,1,0,0)
        self.btn_shuffle = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append([self.btn_shuffle, _("Shuffle")])
        self.btn_shuffle.connect("clicked", self.do_shuffle)
        btn_box.attach(self.btn_shuffle, 1,2,1,2,0,0)
        self.btn_add = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append([self.btn_add, _("My Picture")])
        self.btn_add.connect("clicked", self.do_add_image)
        btn_box.attach(self.btn_add, 1,2,2,3,0,0)
        self.btn_hint = prepare_btn(gtk.Button(" "), 200)
        self.labels_to_translate.append([self.btn_hint, _("Board Hint")])
        self.btn_hint.connect("pressed", self.do_show_hint, True)
        self.btn_hint.connect("released", self.do_show_hint, False)
        btn_box.attach(self.btn_hint, 1,2,3,4,0,0)
        control_panel_box.pack_start(btn_box, False)

        # Control panel end
        panel.pack_start(control_panel, expand=True, fill=True)

        inner_table.attach(panel, 0,1,0,1,0)

        self.game_box = BorderFrame(border_color=COLOR_FRAME_GAME)
        self.game_box.add(self.game)
        inner_table.attach(self.game_box, 1,2,0,1)

        lang_combo = prepare_btn(LanguageComboBox('org.worldwideworkshop.olpc.JigsawPuzzle'))
        lang_combo.connect('changed', self.do_select_language)
        lang_combo.install()
        lang_box = BorderFrame(bg_color=COLOR_BG_CONTROLS,
                               border_color=COLOR_FRAME_CONTROLS)
        hbox = gtk.HBox(False)
        vbox = gtk.VBox(False)
        vbox.pack_start(lang_combo, padding=8)
        hbox.pack_start(vbox, padding=8)
        lang_box.add(hbox)
        inner_table.attach(lang_box, 0,1,1,2,gtk.FILL, gtk.FILL)

        timer_box = BorderFrame(border=BORDER_ALL_BUT_LEFT,
                                bg_color=COLOR_BG_CONTROLS,
                                border_color=COLOR_FRAME_CONTROLS)
        timer_hbox = gtk.HBox(False)
        self.timer = TimerWidget(bg_color=COLOR_BG_BUTTONS[0][1],
                                 fg_color=COLOR_FG_BUTTONS[0][1],
                                 lbl_color=COLOR_BG_BUTTONS[1][1])
        self.timer.set_sensitive(False)
        self.timer.set_border_width(3)
        self.labels_to_translate.append((self.timer, _("Time: ")))
        timer_hbox.pack_start(self.timer, False, padding=8)
        timer_hbox.pack_start(gtk.Label(), True)
        self.btn_lesson = prepare_btn(gtk.Button(" "))
        self.labels_to_translate.append([self.btn_lesson, _("Lesson Plans")])
        self.btn_lesson.connect("clicked", self.do_lesson_plan)
        timer_hbox.pack_start(self.btn_lesson, False, padding=8)
        vbox = gtk.VBox(False)
        vbox.pack_start(timer_hbox, padding=8)
        timer_box.add(vbox)
        inner_table.attach(timer_box, 1,2,1,2,gtk.FILL, gtk.FILL)
        #panel.pack_start(lang_box, expand=False, fill=False)

        self.do_select_language(lang_combo)
        
        if not parent._shared_activity:
            self.do_select_category(self)

    def do_select_category (self, o, *args):
        if isinstance(o, CategorySelector):
            self.thumb.set_image_dir(args[0])
            #if not self.thumb.category.has_images():
            #    self.do_add_image(None)
        else:
            if self.game.get_parent():
                s = CategorySelector(_("Choose a Subject"), self.thumb.get_image_dir())
                s.connect("selected", self.do_select_category)
                s.show()
                self.game_box.push(s)
                s.grab_focus()
            else:
                self.game_box.pop()


    def do_shuffle (self, o, *args):
        if self.thumb.has_image():
            print ("FN", self.thumb.category.filename)
            if not self.game.get_parent():
                self.game_box.pop()
                while gtk.events_pending():
                    gtk.main_iteration(False)
            c = gtk.gdk.Cursor(gtk.gdk.WATCH)
            self.window.set_cursor(c)
            self.game.prepare_image(utils.load_image(self.thumb.get_filename()))
            self.window.set_cursor(None)
            #self.game.randomize()
            self.timer.reset(False)

    
    def do_solve (self, o, *args):
        if not self.game.is_running():
            return
        if not self.game.get_parent():
            self.game_box.pop()
        self.game.solve()
        self.timer.stop(True)

    def do_add_image (self, o, *args):
        self.thumb.add_image()

    def do_select_language (self, combo, *args):
        self.selected_lang_details = combo.translations[combo.get_active()]
        self.refresh_labels()

    def do_show_hint (self, o, show, *args):
        if self.game.get_parent():
            self.game.show_hint(show)

    def refresh_labels (self, first_time=False):
        self._parent.set_title(_("Jigsaw Puzzle Activity"))
        for lbl in self.labels_to_translate:
            if isinstance(lbl[0], gtk.Button):
                lbl[0].get_child().set_label(_(lbl[1]))
            else:
                lbl[0].set_label(_(lbl[1]))
        if not self.game.get_parent() and not first_time:
            self.game_box.pop()
            if isinstance(self.game_box.get_child(), NotebookReaderWidget):
                m = self.do_lesson_plan
            else:
                m = self.do_select_category
            m(self)

    def do_lesson_plan (self, btn):
        if isinstance(self.game_box.get_child(), NotebookReaderWidget):
            self.game_box.pop()
        else:
            s = NotebookReaderWidget('lessons', self.selected_lang_details)
            s.connect('parent-set', self.do_lesson_plan_reparent)
            s.show_all()
            self.game_box.push(s)
            self.timer.stop()

    def do_lesson_plan_reparent (self, widget, oldparent):
        if widget.parent is None:
            self.set_button_translation(self.btn_lesson, "Lesson Plans")
            self.btn_lesson.get_child().set_label(_("Lesson Plans"))
        else:
            self.set_button_translation(self.btn_lesson, "Close Lesson")
            self.btn_lesson.get_child().set_label(_("Close Lesson"))

    def set_piece_cut (self, btn, cutter, *args):
        if isinstance(btn, gtk.ToggleButton) and not btn.get_active():
            for b in (self.btn_basic_cut, self.btn_simple_cut, self.btn_classic_cut):
                if b.get_active():
                    return
            btn.set_active(True)
            return
        self.game.set_cutter(cutter)
        if self.game.is_running():
            self.do_shuffle(btn)
        if isinstance(btn, gtk.ToggleButton):
            for b in (self.btn_basic_cut, self.btn_simple_cut, self.btn_classic_cut):
                if b is not btn:
                    b.set_active(False)

    def set_level (self, btn, level, *args):
        if isinstance(btn, gtk.ToggleButton) and not btn.get_active():
            for b in (self.btn_easy_level, self.btn_normal_level, self.btn_hard_level):
                if b.get_active():
                    return
            btn.set_active(True)
            return
        self.game.set_level(level)
        if self.game.is_running():
            self.do_shuffle(btn)
        if isinstance(btn, gtk.ToggleButton):
            for b in (self.btn_easy_level, self.btn_normal_level, self.btn_hard_level):
                if b is not btn:
                    b.set_active(False)


    def piece_pick_cb (self, *args):
        print "PICKED"
        if not self.timer.is_running():
            self.timer.start()

