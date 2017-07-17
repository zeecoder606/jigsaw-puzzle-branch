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
from gi.repository import Gtk, Gdk, GObject, GdkPixbuf, Pango
import os

from mamamedia_modules import BorderFrame, BORDER_ALL_BUT_BOTTOM, BORDER_ALL_BUT_LEFT
from mamamedia_modules import utils

from mamamedia_modules import ImageSelectorWidget
from mamamedia_modules import LanguageComboBox
from mamamedia_modules import TimerWidget
from mamamedia_modules import BuddyPanel, BUDDYMODE_COLLABORATION

from mamamedia_modules import GAME_IDLE, GAME_STARTED, GAME_FINISHED

from JigsawPuzzleWidget import JigsawPuzzleWidget
from sugar3 import mime
from sugar3.graphics.objectchooser import ObjectChooser
from sugar3.activity.activity import get_bundle_path
import logging
from mamamedia_modules import json

#from gettext import gettext as _

# Colors from Rich's UI design

COLOR_FRAME_OUTER = "#B7B7B7"
COLOR_FRAME_GAME = "#FF0099"
COLOR_FRAME_THUMB = COLOR_FRAME_GAME
COLOR_FRAME_CONTROLS = "#FFFF00"
COLOR_BG_CONTROLS = "#66CC00"
COLOR_FG_BUTTONS = (
    (Gtk.StateType.NORMAL,"#CCFF99"),
    (Gtk.StateType.ACTIVE,"#CCFF99"),
    (Gtk.StateType.PRELIGHT,"#CCFF99"),
    (Gtk.StateType.SELECTED,"#CCFF99"),
    (Gtk.StateType.INSENSITIVE,"#CCFF99"),
    )
COLOR_BG_BUTTONS = (
    (Gtk.StateType.NORMAL,"#027F01"),
    (Gtk.StateType.ACTIVE,"#014D01"),
    (Gtk.StateType.PRELIGHT,"#016D01"),
    (Gtk.StateType.SELECTED,"#027F01"),
    (Gtk.StateType.INSENSITIVE,"#CCCCCC"),
    )

def prepare_btn(btn, w=-1, h=-1):
    for state, color in COLOR_BG_BUTTONS:
        btn.modify_bg(state, Gdk.color_parse(color))
    c = btn.get_child()
    if c is not None:
        for state, color in COLOR_FG_BUTTONS:
            c.modify_fg(state, Gdk.color_parse(color))
    else:
        for state, color in COLOR_FG_BUTTONS:
            btn.modify_fg(state, Gdk.color_parse(color))
    if w>0 or h>0:
        btn.set_size_request(w, h)
    return btn


class JigsawPuzzleUI (BorderFrame):
    __gsignals__ = {'game-state-changed' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (int,))}
    
    def __init__(self, parent):
        super(JigsawPuzzleUI, self).__init__(border_color=COLOR_FRAME_OUTER)

        self._shuffling = False

        self._parent = parent
        # We want the translatables to be detected but not yet translated
        global _
        _ = lambda x: x
        self.labels_to_translate = []

        self._state = GAME_IDLE
        self._readonly = False
        self._join_time = 0

        inner_table = Gtk.Table(2,2,False)
        self.add(inner_table)

        self.game = JigsawPuzzleWidget()
        self.game.connect('picked', self.piece_pick_cb, False)
        self.game.connect('dropped', self.piece_drop_cb)
        self.game.connect('solved', self.do_solve)
        self.game.show()

        # panel is a holder for everything on the left side down to (not inclusive) the language dropdown
        panel = Gtk.VBox()

        # Logo image
        img_logo = Gtk.Image()
        img_logo.set_from_file("icons/logo.png")
        img_logo.show()
        panel.pack_start(img_logo, False, False, 0)


        # Control panel has the image controls
        control_panel = BorderFrame(border=BORDER_ALL_BUT_BOTTOM,
                                    border_color=COLOR_FRAME_CONTROLS,
                                    bg_color=COLOR_BG_CONTROLS)
        control_panel_box = Gtk.VBox()

        scrolled = Gtk.ScrolledWindow()
        scrolled.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        scrolled.props.vscrollbar_policy = Gtk.PolicyType.AUTOMATIC
        scrolled.show()
        scrolled.add_with_viewport(control_panel_box)
        scrolled.get_child().modify_bg(Gtk.StateType.NORMAL, Gdk.color_parse(COLOR_BG_CONTROLS))
        control_panel.add(scrolled)

        spacer = Gtk.Label()
        spacer.set_size_request(-1, 5)
        control_panel_box.pack_start(spacer, False, False, 0)

        #btn_box = Gtk.Table(2,5,False)
        #btn_box.set_col_spacings(5)
        #btn_box.set_row_spacings(5)
        #btn_box.attach(Gtk.Label(), 0,1,0,2)
        # Cut type buttons
        self.btn_basic_cut = Gtk.ToggleButton()
        #i = Gtk.Image()
        #i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'cut_basic.svg')))
        #self.btn_basic_cut.set_image(i)
        #btn_box.attach(prepare_btn(self.btn_basic_cut), 1,2,0,1,0,0)
        self.btn_simple_cut = Gtk.ToggleButton()
        #i = Gtk.Image()
        #i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'cut_simple.svg')))
        #self.btn_simple_cut.set_image(i)
        #btn_box.attach(prepare_btn(self.btn_simple_cut), 2,3,0,1,0,0)
        self.btn_classic_cut = Gtk.ToggleButton()
        #i = Gtk.Image()
        #i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'cut_classic.svg')))
        #self.btn_classic_cut.set_image(i)
        ## Link cutter buttons with cutter styles
        self.btn_cut_mapping = {
            'basic': self.btn_basic_cut,
            'simple': self.btn_simple_cut,
            'classic': self.btn_classic_cut,
            }
        for k,v in self.btn_cut_mapping.items():
            v.connect("released", self.set_piece_cut, k)

        #btn_box.attach(prepare_btn(self.btn_classic_cut), 3,4,0,1,0,0)
        ## Difficulty level buttons
        self.btn_easy_level = Gtk.ToggleButton()
        #i = Gtk.Image()
        #i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'level_easy.svg')))
        #self.btn_easy_level.set_active(True)
        #self.btn_easy_level.set_image(i)
        #btn_box.attach(prepare_btn(self.btn_easy_level), 1,2,1,2,0,0)
        self.btn_normal_level = Gtk.ToggleButton()
        #i = Gtk.Image()
        #i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'level_normal.svg')))
        #self.btn_normal_level.set_image(i)
        #btn_box.attach(prepare_btn(self.btn_normal_level), 2,3,1,2,0,0)
        self.btn_hard_level = Gtk.ToggleButton()
        #i = Gtk.Image()
        #i.set_from_pixbuf(utils.load_image(os.path.join('icons', 'level_hard.svg')))
        #self.btn_hard_level.set_image(i)
        ## Link level buttons with levels
        self.btn_level_mapping = {
            3: self.btn_easy_level,
            5: self.btn_normal_level,
            8: self.btn_hard_level,
            }
        for k,v in self.btn_level_mapping.items():
            v.connect("released", self.set_level, k)

        #btn_box.attach(prepare_btn(self.btn_hard_level), 3,4,1,2,0,0)
        
        #btn_box.attach(Gtk.Label(), 4,5,0,2)
        #control_panel_box.pack_start(btn_box, False, True, 0)

        self.thumb = ImageSelectorWidget(frame_color=COLOR_FRAME_THUMB,
                                         prepare_btn_cb=prepare_btn,
                                         method=utils.RESIZE_PAD,
                                         image_dir="images",
                                         parent=self._parent)
        control_panel_box.pack_start(self.thumb, False, True, 0)

        spacer = Gtk.Label()
        spacer.set_size_request(-1, 5)
        control_panel_box.pack_start(spacer, False, False, 0)
        
        # The game control buttons
        #btn_box = Gtk.Table(3,4,False)
        #btn_box.set_row_spacings(2)
        #btn_box.attach(Gtk.Label(), 0,1,0,4)
        #btn_box.attach(Gtk.Label(), 2,3,0,4)
        self.btn_solve = prepare_btn(Gtk.Button(" "), 200)
        #self.labels_to_translate.append([self.btn_solve, _("Solve")])
        #self.btn_solve.connect("clicked", self.do_solve)
        #btn_box.attach(self.btn_solve, 1,2,0,1,0,0)
        self.btn_shuffle = prepare_btn(Gtk.Button(" "), 200)
        #self.labels_to_translate.append([self.btn_shuffle, _("Shuffle")])
        #self.btn_shuffle.connect("clicked", self.do_shuffle)
        #btn_box.attach(self.btn_shuffle, 1,2,1,2,0,0)
        self.btn_add = prepare_btn(Gtk.Button(" "), 200)
        #self.labels_to_translate.append([self.btn_add, _("My Picture")])
        #self.btn_add.connect("clicked", self.do_add_image)
        #btn_box.attach(self.btn_add, 1,2,2,3,0,0)
        self.btn_hint = prepare_btn(Gtk.ToggleButton(" "), 200)
        #self.labels_to_translate.append([self.btn_hint, _("Board Hint")])
        #self.btn_hint.connect("clicked", self.do_show_hint)
        #btn_box.attach(self.btn_hint, 1,2,3,4,0,0)
        #control_panel_box.pack_start(btn_box, False)
        self.control_panel_box = control_panel_box

        # Control panel end
        panel.pack_start(control_panel, True, True, 0)

        inner_table.attach(panel, 0,1,0,1,0)

        self.game_box = BorderFrame(border_color=COLOR_FRAME_GAME)
        self.game_box.add(self.game)

        self.notebook = Gtk.Notebook()
        self.notebook.show()
        self.notebook.props.show_border = False
        self.notebook.props.show_tabs = False
        self.notebook.append_page(self.game_box, None)
        inner_table.attach(self.notebook, 1,2,0,1)

        lang_combo = prepare_btn(LanguageComboBox('org.worldwideworkshop.olpc.JigsawPuzzle'))
        lang_combo.connect('changed', self.do_select_language)
        # Push the gettext translator into the global namespace
        del _
        lang_combo.install()
        lang_box = BorderFrame(bg_color=COLOR_BG_CONTROLS,
                               border_color=COLOR_FRAME_CONTROLS)
        hbox = Gtk.HBox(False)
        vbox = Gtk.VBox(False)
        vbox.pack_start(lang_combo, True, True, 8)
        hbox.pack_start(vbox, True, True, 8)
        lang_box.add(hbox)
        inner_table.attach(lang_box, 0,1,1,2,Gtk.AttachOptions.FILL, Gtk.AttachOptions.FILL)

        timer_box = BorderFrame(border=BORDER_ALL_BUT_LEFT,
                                bg_color=COLOR_BG_CONTROLS,
                                border_color=COLOR_FRAME_CONTROLS)
        timer_hbox = Gtk.HBox(False)
        self.timer = TimerWidget(bg_color=COLOR_BG_BUTTONS[0][1],
                                 fg_color=COLOR_FG_BUTTONS[0][1],
                                 lbl_color=COLOR_BG_BUTTONS[1][1])
        self.timer.set_sensitive(False)
        self.timer.set_border_width(3)
        self.labels_to_translate.append((self.timer, _("Time: ")))
        timer_hbox.pack_start(self.timer, False, True, 8)
        self.timer.connect('timer_toggle', self.timer_toggle_cb)

        self.msg_label = Gtk.Label()
        self.msg_label.show()
        timer_hbox.pack_start(self.msg_label, True, True, 0)
        
        self.do_select_language(lang_combo)
        
        self.buddy_panel = BuddyPanel(BUDDYMODE_COLLABORATION)
        self.buddy_panel.show()

        self.set_contest_mode(False)
        self.initial_path = os.path.join(
            get_bundle_path(), 'images', 'image_atih_h250_w250_lg.gif')
        self.tpb = utils.load_image(self.initial_path)
        self.tpbb = utils.resize_image(self.tpb, 200, 200, method=2)
        self.thumb.image.set_from_pixbuf(self.tpbb)
        self.pbb = self.tpb
        self.yy = None
        #self.do_shuffle()

        # Assert consistent state
        #self.cutter_change_cb(None, self.game.get_cutter(), self.game.get_target_pieces_per_line())
        
        #self.initial_path = os.path.join(
        #    get_bundle_path(), 'images', 'image_atih_h250_w250_lg.gif')
        #self.show_image(self.initial_path)

    def set_message (self, msg, frommesh=False):
        if frommesh and self.get_game_state() != GAME_STARTED:
            return
        self.msg_label.set_label(msg)

    def _set_control_area (self, *args):
        """ The controls area below the logo needs different actions when in contest mode,
        and also if we are the contest initiators or not. """
        if self._contest_mode:
            if self.get_game_state() > GAME_IDLE or not self.is_initiator():
                self.set_readonly()
            if self.get_game_state() <= GAME_IDLE:
                if self.is_initiator():
                    if self.timer.is_reset():
                        self.set_message(_("Select image and press Start Game..."))
                    else:
                        self.set_game_state(GAME_STARTED)
                else:
                    self.set_message(_("Waiting for Puzzle image to be chosen..."))
                    self.set_button_translation(self.btn_add, "Buddies")
                    self.btn_add.get_child().set_label(_("Buddies"))

    def set_readonly (self):
        """ In collaborative mode, after an image is selected and the game started you can not change much """
        #self.thumb.set_readonly(True)
        self.set_button_translation(self.btn_shuffle, "Game Running")
        self.btn_shuffle.get_child().set_label(_("Game Running"))
        self.btn_shuffle.set_sensitive(False)
        for b in self.btn_cut_mapping.values() + self.btn_level_mapping.values():
            if not (b.get_active() and self.is_initiator()):
                b.set_sensitive(False)
        self._readonly = True

    def is_readonly (self):
        return self._readonly

    def is_initiator (self):
        return self._parent.initiating

    @utils.trace
    def timer_toggle_cb (self, evt, running):
        logging.debug("Timer running: %s" % str(running))
        if self._contest_mode and running:
            self.set_game_state(GAME_STARTED)
        self._send_status_update()

    def set_contest_mode (self, mode):
        if getattr(self, '_contest_mode', None) != mode:
            self.timer.set_can_stop(not bool(mode))
            self._contest_mode = bool(mode)
            self._set_control_area()
            if self._contest_mode:
                self.btn_solve.set_sensitive(False)
                self.set_button_translation(self.btn_solve, "Give Up")
                self.btn_solve.get_child().set_label(_("Give Up"))
                self.set_button_translation(self.btn_shuffle, "Start Game")
                self.btn_shuffle.get_child().set_label(_("Start Game"))

    @utils.trace
    def set_game_state (self, state, force=False):
        if state[0] > self._state[0] or force:
            self._state = state
            self.emit('game-state-changed', state[0])
            self._set_control_area()
            if state == GAME_STARTED:
                self.set_button_translation(self.btn_add, "Buddies")
                self.btn_add.get_child().set_label(_("Buddies"))
                if self._contest_mode:
                    if self.is_initiator():
                        self._send_game_update()
            self._send_status_update()
        elif state[0] <= GAME_STARTED[0] and self._contest_mode and not self.is_initiator():
            c = Gdk.Cursor.new(Gdk.CursorType.WATCH)
            #self.window.set_cursor(c)
            

    def get_game_state (self):
        return self._state

    


    @utils.trace
    def _show_game (self, pixbuf=None, reshuffle=True):
        if not self.game.get_parent():
            self.game_box.pop()
            while Gtk.events_pending():
                Gtk.main_iteration(False)
        c = Gdk.Cursor.new(Gdk.CursorType.WATCH)
        #self.window.set_cursor(c)
        if not self.game.prepare_image(pixbuf, reshuffle):
            self._shuffling = False
            return
        self._shuffling = False
        #self.window.set_cursor(None)
        #self.game.randomize()

    def show_image(self, path):
        
        self.pbb = utils.load_image(path)
        self.yy = path
        self._show_game(self.pbb)
        self.timer.reset(False)
        self.do_show_hint(self.btn_hint)
        self.fnpbb = utils.resize_image(self.pbb, 200, 200, method=2)
        self.thumb.image.set_from_pixbuf(self.fnpbb)


    def do_shuffle (self, o, *args):
        #if self.thumb.has_image():
        #    print ("FN", self.thumb.category.filename)
        if self._contest_mode and \
             self.get_game_state() == GAME_IDLE and \
             self.game.is_running() and \
             o == self.btn_shuffle and \
             self.timer.is_reset():
            # Start
            logging.debug('do_shuffle')
            self.timer.start()
        else :
            if not self._shuffling:
                logging.debug('do_shuffle start')
                self.timer.stop()
                self._shuffling = True
                self._show_game(self.pbb)
                self.timer.reset(False)
                self.do_show_hint(self.btn_hint)
        
    def do_solve (self, o, *args):
        if not self.game.is_running():
            return
        if not self.game.get_parent():
            self.game_box.pop()
        self.game.solve()
        self.timer.stop(True)
        if self._contest_mode:
            self.set_game_state(GAME_FINISHED)
            self.set_message(_("Puzzle Solved!"))
            self.control_panel_box.foreach(self.control_panel_box.remove)
            lbl = Gtk.Label(label=_("Press Stop on the Toolbar to Exit Activity!"))
            lbl.modify_font(Pango.FontDescription("bold 9"))
            lbl.set_line_wrap(True)
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_size_request(200, -1)
            lbl.show()
            self.control_panel_box.pack_start(lbl, True, True, 0)
            

    def do_add_image (self, o, *args):
        if self._contest_mode and self.get_game_state() >= GAME_STARTED:
            # Buddy Panel
            if not self.buddy_panel.get_parent():
                #self.timer.stop()
                self.game_box.push(self.buddy_panel)
            else:
                self.game_box.pop()
        else:
            self.add_image()

    def add_image (self, *args):#widget=None, response=None, *args):
        """ Use to trigger and process the My Own Image selector. """

        if hasattr(mime, 'GENERIC_TYPE_IMAGE'):
            chooser = ObjectChooser(_('Choose image'), self._parent,
                                    Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                                    what_filter=mime.GENERIC_TYPE_IMAGE)
        else:
            chooser = ObjectChooser(_('Choose image'), self._parent,
                                    Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT)

        try:
            result = chooser.run()
            if result == Gtk.ResponseType.ACCEPT:
                jobject = chooser.get_selected_object()
                if jobject and jobject.file_path:
                    self.show_image(str(jobject.file_path))
                    pass
    
        finally:
            chooser.destroy()
            del chooser

    @utils.trace
    def do_select_language (self, combo, *args):
        self.selected_lang_details = combo.translations[combo.get_active()]
        self.refresh_labels()

    def do_show_hint (self, o, *args):
        self.game.show_hint(o.get_active())

    def set_button_translation (self, btn, translation):
        for i in range(len(self.labels_to_translate)):
            if self.labels_to_translate[i][0] == btn:
                self.labels_to_translate[i][1] = translation
                break

    def refresh_labels (self, first_time=False):
        self._parent.set_title(_("Jigsaw Puzzle Activity"))
        for lbl in self.labels_to_translate:
            if isinstance(lbl[0], Gtk.Button):
                lbl[0].get_child().set_label(_(lbl[1]))
            else:
                lbl[0].set_label(_(lbl[1]))
        if not self.game.get_parent() and not first_time:
            self.game_box.pop()
            if self.notebook.get_current_page() == 1:
                m = self.do_lesson_plan
            else:
                pass
            m(self)

    def set_piece_cut (self, btn, cutter, *args):
        if self.is_readonly():
            return
        self.game.set_cutter(cutter)
        if self.game.is_running():
            self.do_shuffle(btn)

    def set_level (self, btn, level, *args):
        if self.is_readonly():
            return
        self.game.set_target_pieces_per_line(level)
        if self.game.is_running():
            self.do_shuffle(btn)

    def piece_pick_cb (self, o, piece, from_mesh=False):
        if not self.timer.is_running():
            self.timer.start()
        if not from_mesh:
            self._send_pick_notification (piece)

    def piece_drop_cb (self, o, piece, from_mesh=False):
        if self._parent.shared_activity and not from_mesh:
            self._send_drop_notification (piece)

    def _freeze (self, journal=True):
        if journal:
            return {'thumb': os.path.join(get_bundle_path(), 'images'), 'filename': self.yy,
                    'timer': self.timer._freeze(),
                    'game': self.game._freeze(),
                    }
        else:
            return {'timer': self.timer._freeze(),
                    'game': self.game._freeze(img_cksum_only=True),}

    def _thaw (self, data):
        self.timer.reset()
        for k in ('thumb', 'timer', 'game'):
            if data.has_key(k):
                logging.debug('_thaw data for %s: %s' % (k, data))
                getattr(self, k)._thaw(data[k])
        if data.has_key('game'):# and not data.has_key('thumb'):           
            self.thumb.image.set_from_pixbuf(self.fnpbb)
        if data.has_key('timer'):
            self._join_time = self.timer.ellapsed()
        if data.has_key('game') and data['game']['piece_pos']:
            self._show_game(reshuffle=False)

    @utils.trace
    def _send_status_update (self):
        """ Send a status update signal """
        if self._parent.shared_activity:
            if self.get_game_state() == GAME_STARTED:
                
                self.set_message(_("Game Started!"))
                #self.set_message(_("Waiting for Puzzle image to be transferred..."))
            self._parent.game_tube.StatusUpdate(self._state[1], self._join_time)

    @utils.trace
    def _send_game_update (self):
        """ A puzzle was selected, share it """
        if self._parent.shared_activity:
            # TODO: Send image 
            self._parent.game_tube.GameUpdate(self._state[1])

    @utils.trace
    def _send_pick_notification (self, piece):
        """ """
        if self._parent.shared_activity:
            self._parent.game_tube.PiecePicked(piece.get_index())

    @utils.trace
    def _recv_pick_notification (self, index):
        for piece in self.game.get_floating_pieces():
            if piece.get_index() == index:
                logging.debug("Remote picked piece %s" % piece)
                piece.set_sensitive(False)
                
    @utils.trace
    def _send_drop_notification (self, piece):
        """ """
        if piece.placed:
            self._parent.game_tube.PiecePlaced(piece.get_index())
        else:
            self._parent.game_tube.PieceDropped(piece.get_index(), piece.get_position())
    
    @utils.trace
    def _recv_drop_notification (self, index, position=None):
        for piece in self.game.get_floating_pieces():
            if piece.get_index() == index:
                logging.debug("Moving piece %s" % piece)
                if position is None:
                    self.game.board.place_piece(piece)
                else:
                    self.game._move_cb(piece, position[0], position[1], absolute=True)
                    self.game._drop_cb(piece, from_mesh=True)
                piece.set_sensitive(True)
                break
