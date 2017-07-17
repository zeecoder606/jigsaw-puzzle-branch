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

# init gthreads before using abiword
import gi
from gi.repository import GObject
GObject.threads_init()
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GdkPixbuf
from sugar3.activity.activity import Activity, get_bundle_path
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toggletoolbutton import ToggleToolButton
from gettext import gettext as _
import logging, os, sys
import time
import zlib
from cStringIO import StringIO
from mamamedia_modules import json

from JigsawPuzzleUI import JigsawPuzzleUI
from mamamedia_modules import TubeHelper
from mamamedia_modules import GAME_IDLE, GAME_STARTED, GAME_FINISHED, GAME_QUIT

logger = logging.getLogger('jigsawpuzzle-activity')

from dbus.service import method, signal
from dbus.gobject_service import ExportedGObject

SERVICE = "org.worldwideworkshop.olpc.JigsawPuzzle.Tube"
IFACE = SERVICE
PATH = "/org/worldwideworkshop/olpc/JigsawPuzzle/Tube"

class GameTube (ExportedGObject):
    """ Manage the communication between cooperating activities """
    def __init__(self, tube, is_initiator, activity):
        super(GameTube, self).__init__(tube, PATH)
        self.tube = tube
        self.activity = activity
        self.add_status_update_handler()
        self.get_buddy = activity._get_buddy
        self.syncd_once = False
        if is_initiator:
            self.add_hello_handler()
            self.add_request_image_handler()
            #self.add_need_image_handler()
            #self.activity.ui.connect('game-state-changed', self.game_state_cb)
        else:
            self.add_game_update_handler()
            #self.add_re_sync_handler()
            self.Hello()
        self.add_piece_picked_handler()
        self.add_piece_placed_handler()
        self.add_piece_dropped_handler()
        self.tube.watch_participants(self.participant_change_cb)

    def participant_change_cb(self, added, removed):
        logger.debug('Adding participants: %r', added)
        logger.debug('Removing participants: %r', removed)


    ###############
    # Signals
    
    @signal(dbus_interface=IFACE, signature='')
    def Hello(self):
        """Request that this player's Welcome method is called to bring it
        up to date with the game state.
        """

    @signal(dbus_interface=IFACE, signature='s')
    def GameUpdate(self, game_state):
        """ When an image is chosen by the initiator, this method gets called."""

    @signal(dbus_interface=IFACE, signature='su')
    def StatusUpdate (self, status, ellapsed_time):
        """ signal a reshufle, possibly with a new image """

    @signal(dbus_interface=IFACE, signature='')
    def RequestImage (self):
        """ Request that the game image be sent to us. """

    @signal(dbus_interface=IFACE, signature='i')
    def PiecePicked (self, index):
        """ Signals a piece picked in the correct board position """
        
    @signal(dbus_interface=IFACE, signature='i')
    def PiecePlaced (self, index):
        """ Signals a piece placed in the correct board position """
        
    @signal(dbus_interface=IFACE, signature='i(dd)')
    def PieceDropped (self, index, position):
        """ Signals a piece that has been moved around and dropped """

    ###############
    # Callbacks

    def add_hello_handler(self):
        self.tube.add_signal_receiver(self.hello_cb, 'Hello', IFACE,
                                                                    path=PATH, sender_keyword='sender')

    def hello_cb(self, obj=None, sender=None):
        """Tell the newcomer what's going on."""
        logger.debug('Newcomer %s has joined', sender)
#       if self.activity.ui.get_game_state() < GAME_STARTED:
#           f = {}
#       else:
#           f = self.activity.ui._freeze(journal=False)
        self.tube.get_object(sender, PATH).Welcome(self.activity.ui.get_game_state()[1], dbus_interface=IFACE)

    def add_game_update_handler (self):
        self.tube.add_signal_receiver(self.game_update_cb, 'GameUpdate', IFACE,
                                                                    path=PATH, sender_keyword='sender')

    def game_update_cb (self, game_state, sender=None):
        logger.debug('GameUpdate: %s' % game_state)
        if game_state == GAME_STARTED[1]:
            self.activity.ui.set_game_state(GAME_STARTED)
            self.RequestImage()
        #self.activity.ui.set_game_state(str(game_state))
        #self.activity.ui._thaw(json.read(str(state)))

    def add_request_image_handler (self):
        self.tube.add_signal_receiver(self.request_image_cb, 'RequestImage', IFACE,
                                                                    path=PATH, sender_keyword='sender')

    def request_image_cb (self, sender=None):
        logger.debug('Sending image to %s', sender)
        img = self.activity.ui.game.board.cutboard.get_image_as_png()
        t = time.time()
        compressed = zlib.compress(img, 9)
        # We will be sending the image, 24K at a time (my tests put the high water at 48K)
        logger.debug("was %d, is %d. compressed to %d%% in %0.4f seconds" % (len(img), len(compressed), len(compressed)*100/len(img), time.time() - t))
        part_size = 24*1024
        parts = len(compressed) / part_size
        for i in range(parts+1):
            self.tube.get_object(sender, PATH).ImageSync(compressed[i*part_size:(i+1)*part_size], i+1,
                                                         dbus_interface=IFACE)
        self.tube.get_object(sender, PATH).ImageDetailsSync(json.write(self.activity.ui._freeze(journal=False)), dbus_interface=IFACE)


    def add_piece_picked_handler (self):
        self.tube.add_signal_receiver(self.piece_picked_cb, 'PiecePicked', IFACE,
                                                                    path=PATH, sender_keyword='sender')

    def piece_picked_cb (self, index, sender=None):
        if sender != self.activity.get_bus_name():
            self.activity.ui._recv_pick_notification(index)

    def add_piece_placed_handler (self):
        self.tube.add_signal_receiver(self.piece_placed_cb, 'PiecePlaced', IFACE,
                                                                    path=PATH, sender_keyword='sender')

    def piece_placed_cb (self, index, sender=None):
        if sender != self.activity.get_bus_name():
            self.activity.ui._recv_drop_notification(index)
    
    def add_piece_dropped_handler (self):
        self.tube.add_signal_receiver(self.piece_dropped_cb, 'PieceDropped', IFACE,
                                                                    path=PATH, sender_keyword='sender')

    def piece_dropped_cb (self, index, position, sender=None):
        if sender != self.activity.get_bus_name():
            self.activity.ui._recv_drop_notification(index, position)

    def add_status_update_handler(self):
        self.tube.add_signal_receiver(self.status_update_cb, 'StatusUpdate', IFACE,
                                                                    path=PATH, sender_keyword='sender')

    def status_update_cb (self, status, join_time, sender=None):
        buddy = self.get_buddy(self.tube.bus_name_to_handle[sender])
        logger.debug("status_update: %s %s" % (str(sender), str(join_time)))
        nick, stat = self.activity.ui.buddy_panel.update_player(buddy, status, True, int(join_time))
        if buddy != self.activity.owner:
            self.activity.ui.set_message(
                    _("Buddy '%(buddy)s' changed status: %(status)s") % \
                        {'buddy': nick, 'status': stat},
                    frommesh=True)
    
    ##############
    # Methods

    @method(dbus_interface=IFACE, in_signature='s', out_signature='')
    def Welcome(self, game_state):
        """ """
        logger.debug("state: '%s' (%s)" % (game_state, type(game_state)))
        if game_state == GAME_STARTED[1]:
            self.activity.ui.set_game_state(GAME_STARTED)
            self.RequestImage()
        else:
            self.activity.ui.set_game_state(GAME_IDLE)

    @method(dbus_interface=IFACE, in_signature='ayi', out_signature='', byte_arrays=True)
    def ImageSync (self, image_part, part_nr):
        """ """
        logger.debug("Received image part #%d, length %d" % (part_nr, len(image_part)))
        if part_nr == 1:
            self.image = StringIO()
            self.image.write(image_part)
        else:
            self.image.write(image_part)

    @method(dbus_interface=IFACE, in_signature='s', out_signature='', byte_arrays=True)
    def ImageDetailsSync (self, state):
        """ Signals end of image and shares the rest of the needed data to create the image remotely."""
        state = json.read(str(state))
        state['game']['board']['cutboard']['pb'] = zlib.decompress(self.image.getvalue())
        self.activity.ui._thaw(state)
        self.activity.ui._send_status_update()
        

class JigsawPuzzleActivity(Activity, TubeHelper):
    def __init__(self, handle):
        Activity.__init__(self, handle)
        logger.debug('Starting Jigsaw Puzzle activity... %s' % str(get_bundle_path()))
        os.chdir(get_bundle_path())

        self.connect('destroy', self._destroy_cb)
        
        self._sample_window = None
        self.fixed = Gtk.Fixed()
        self.ui = JigsawPuzzleUI(self)
        toolbar_box = ToolbarBox()
        self.set_toolbar_box(toolbar_box)
        toolbar_box.show()
        activity_button = ActivityToolbarButton(self)
        toolbar_box.toolbar.insert(activity_button, -1)
        activity_button.show()

        self.btn_basic_cut = ToolButton('cut_basic')
        self.btn_basic_cut.set_tooltip(_('Basic style'))
        toolbar_box.toolbar.insert(self.btn_basic_cut, -1)
        #btn_9.set_active(True)
        #btn_9.connect('clicked', self.ui.set_nr_pieces, 9)
        self.btn_basic_cut.show()

        self.btn_simple_cut = ToolButton('cut_simple')
        self.btn_simple_cut.set_tooltip(_('Simple style'))
        toolbar_box.toolbar.insert(self.btn_simple_cut, -1)
        #btn_9.set_active(True)
        #btn_12.connect('clicked', self.ui.set_nr_pieces, 12)
        self.btn_simple_cut.show()

        self.btn_classic_cut = ToolButton('cut_classic')
        self.btn_classic_cut.set_tooltip(_('Classic style'))
        toolbar_box.toolbar.insert(self.btn_classic_cut, -1)
        #btn_9.set_active(True)
        #btn_16.connect('clicked', self.ui.set_nr_pieces, 16)
        self.btn_classic_cut.show()

        self.btn_cut_mapping = {
            'basic': self.btn_basic_cut,
            'simple': self.btn_simple_cut,
            'classic': self.btn_classic_cut,
            }
        for k,v in self.btn_cut_mapping.items():
            v.connect('clicked', self.ui.set_piece_cut, k)

        self.btn_easy_level = ToolButton('level_easy')
        self.btn_easy_level.set_tooltip(_('Easy'))
        toolbar_box.toolbar.insert(self.btn_easy_level, -1)
        #btn_9.set_active(True)
        #btn_solve.connect('clicked', self.ui.do_solve)
        self.btn_easy_level.show()

        self.btn_normal_level = ToolButton('level_normal')
        self.btn_normal_level.set_tooltip(_('Normal'))
        toolbar_box.toolbar.insert(self.btn_normal_level, -1)
        #btn_9.set_active(True)
        #btn_solve.connect('clicked', self.ui.do_solve)
        self.btn_normal_level.show()

        self.btn_hard_level = ToolButton('level_hard')
        self.btn_hard_level.set_tooltip(_('Hard'))
        toolbar_box.toolbar.insert(self.btn_hard_level, -1)
        #btn_9.set_active(True)
        #btn_solve.connect('clicked', self.ui.do_solve)
        self.btn_hard_level.show()

        self.btn_level_mapping = {
            3: self.btn_easy_level,
            5: self.btn_normal_level,
            8: self.btn_hard_level,
            }
        for k,v in self.btn_level_mapping.items():
            v.connect('clicked', self.ui.set_level, k)

        self.btn_solve = ToolButton('dialog-ok')
        self.btn_solve.set_tooltip(_('Solve'))
        toolbar_box.toolbar.insert(self.btn_solve, -1)
        self.btn_solve.connect('clicked', self.ui.do_solve)
        self.btn_solve.show()

        self.btn_shuffle = ToolButton('edit-redo')
        self.btn_shuffle.set_tooltip(_('Shuffle'))
        toolbar_box.toolbar.insert(self.btn_shuffle, -1)
        self.btn_shuffle.connect("clicked", self.ui.do_shuffle)
        self.btn_shuffle.show()


        self.btn_hint = ToggleToolButton('image-load')
        self.btn_hint.set_tooltip(_('Import picture from Journal'))
        toolbar_box.toolbar.insert(self.btn_hint, -1)
        self.btn_hint.connect("clicked", self.ui.do_show_hint)
        self.btn_hint.show()


        self.btn_add = ToolButton('image-load')
        self.btn_add.set_tooltip(_('Import picture from Journal'))
        toolbar_box.toolbar.insert(self.btn_add, -1)
        self.btn_add.connect("clicked", self.ui.do_add_image)
        self.btn_add.show()


        btn_select = ToolButton('imageviewer')
        btn_select.set_tooltip(_('Add Picture'))
        toolbar_box.toolbar.insert(btn_select, -1)
        #btn_9.set_active(True)
        btn_select.connect('clicked', self.do_samples_cb)
        btn_select.show()

  

 
  
    # Toolbar title size hack
        
        
        self.set_canvas(self.ui)

        self.show_all()

        TubeHelper.__init__(self, tube_class=GameTube, service=SERVICE)

    def _destroy_cb(self, data=None):
        return True

    def new_tube_cb (self):
        self.ui.set_contest_mode(True)

    def shared_cb (self):
        self.ui.buddy_panel.add_player(self.owner)

    def joined_cb (self):
        self.ui.set_readonly()

    def buddy_joined_cb (self, buddy):
        nick = self.ui.buddy_panel.add_player(buddy)
        self.ui.set_message(_("Buddy '%s' joined the game!") % (nick), frommesh=True)

    def buddy_left_cb (self, buddy):
        nick = self.ui.buddy_panel.remove_player(buddy)
        self.ui.set_message(_("Buddy '%s' left the game!") % (nick), frommesh=True)

    def read_file(self, file_path):
        f = open(file_path, 'r')
        try:
            session_data = f.read()
        finally:
            f.close()
        self.ui._thaw(json.read(session_data))
        #import urllib
        #logging.debug('Read session: %s.' % urllib.quote(session_data))
        
    def write_file(self, file_path):
        # First make sure the game is showing, as we need that to get the piece positions
        
        session_data = json.write(self.ui._freeze())
        f = open(file_path, 'w')
        try:
            f.write(session_data)
        finally:
            f.close()
       
    def do_samples_cb(self, button):
        self._create_store()

    def _create_store(self, widget=None):
            #if self._sample_window is None:
            
            self.set_canvas(self.fixed)
            self.fixed.show()
            
            self._sample_box = Gtk.EventBox()
            self._sample_window = Gtk.ScrolledWindow()
            self._sample_window.set_policy(Gtk.PolicyType.NEVER,
                                           Gtk.PolicyType.AUTOMATIC)
            width = Gdk.Screen.width() / 2
            height = Gdk.Screen.height() / 2
            self._sample_window.set_size_request(width, height)
            self._sample_window.show()

            store = Gtk.ListStore(GdkPixbuf.Pixbuf, str)

            icon_view = Gtk.IconView()
            icon_view.set_model(store)
            icon_view.set_selection_mode(Gtk.SelectionMode.SINGLE)
            icon_view.connect('selection-changed', self._sample_selected,
                             store)
            icon_view.set_pixbuf_column(0)
            icon_view.grab_focus()
            self._sample_window.add_with_viewport(icon_view)
            icon_view.show()
            self._fill_samples_list(store)

            width = Gdk.Screen.width() / 4
            height = Gdk.Screen.height() / 4

            self._sample_box.add(self._sample_window)
            #_logger.debug('check fixed')
            self.fixed.put(self._sample_box, width, height)
            #self.ui.game_wrapper.add(self._sample_box)
            #self.fixed.show()
            #_logger.debug('fixed comp')
            self._sample_window.show()
            #_logger.debug('window comp')
            self._sample_box.show()
            #_logger.debug('box comp')
            #self.fixed.show_all()
    def _get_selected_path(self, widget, store):
        try:
            iter_ = store.get_iter(widget.get_selected_items()[0])
            image_path = store.get(iter_, 1)[0]

            return image_path, iter_
        except:
            return None

    def _sample_selected(self, widget, store):
        self.set_canvas(self.ui)
        self.show_all()
        selected = self._get_selected_path(widget, store)


        if selected is None:
            self._selected_sample = None
            self._sample_window.hide()
            return
        
        image_path, _iter = selected
        iter_ = store.get_iter(widget.get_selected_items()[0])
        image_path = store.get(iter_, 1)[0]

        self._selected_sample = image_path
        self._sample_window.hide()
        logger.debug(self._selected_sample + 'hello')
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        GObject.idle_add(self._sample_loader)

    def _sample_loader(self):
        # Convert from thumbnail path to sample path
        logger.debug('sample here')
        self.ui.show_image(path = self._selected_sample)
        logger.debug('sample there')
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR)) 

    def _fill_samples_list(self, store):
        '''
        Append images from the artwork_paths to the store.
        '''
        for filepath in self._scan_for_samples():
            pixbuf = None
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                filepath, 100, 100)
            store.append([pixbuf, filepath])
            #_logger.debug('fill comp')
    def _scan_for_samples(self):
        path = os.path.join(get_bundle_path(), 'images')
        samples = []
        for name in os.listdir(path):
            if name.endswith(".gif"):
                samples.append(os.path.join(path, name))
        samples.sort()
        #_logger.debug('scan comp')
        return samples
