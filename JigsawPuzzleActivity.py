from sugar.activity.activity import Activity, ActivityToolbox, get_bundle_path
from gettext import gettext as _
import logging, os, sys
from mamamedia_modules import json

from JigsawPuzzleUI import JigsawPuzzleUI
from mamamedia_modules import TubeHelper

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
		#self.add_status_update_handler()
		self.get_buddy = activity._get_buddy
		self.syncd_once = False
		if is_initiator:
			self.add_hello_handler()
			#self.add_need_image_handler()
			#self.activity.ui.connect('game-state-changed', self.game_state_cb)
		else:
			#self.add_re_sync_handler()
			self.Hello()
		self.tube.watch_participants(self.participant_change_cb)

	def participant_change_cb(self, added, removed):
		logger.debug('Adding participants: %r' % added)
		logger.debug('Removing participants: %r' % type(removed))

	@signal(dbus_interface=IFACE, signature='')
	def Hello(self):
		"""Request that this player's Welcome method is called to bring it
		up to date with the game state.
		"""

	def add_hello_handler(self):
		self.tube.add_signal_receiver(self.hello_cb, 'Hello', IFACE,
																	path=PATH, sender_keyword='sender')

	def hello_cb(self, obj=None, sender=None):
		"""Tell the newcomer what's going on."""
		logger.debug('Newcomer %s has joined', sender)
		f = json.write(self.activity.ui._freeze())
		logger.debug('freeze: %s' % str(json.read(f)))
		self.tube.get_object(sender, PATH).Welcome(f, dbus_interface=IFACE)

	@method(dbus_interface=IFACE, in_signature='s', out_signature='')
	def Welcome(self, state):
		""" """
		logger.debug("state: '%s' (%s)" % (state, type(state)))
		self.activity.ui._thaw(json.read(str(state)))

class JigsawPuzzleActivity(Activity, TubeHelper):
	def __init__(self, handle):
		Activity.__init__(self, handle)
		logger.debug('Starting Jigsaw Puzzle activity... %s' % str(get_bundle_path()))
		os.chdir(get_bundle_path())

		self.connect('destroy', self._destroy_cb)
		
		toolbox = ActivityToolbox(self)
		self.set_toolbox(toolbox)
		toolbox.show()

    # Toolbar title size hack
		title_widget = toolbox._activity_toolbar.title
		title_widget.set_size_request(title_widget.get_layout().get_pixel_size()[0] + 20, -1)
		
		self.ui = JigsawPuzzleUI(self)
		self.set_canvas(self.ui)

		self.show_all()

		TubeHelper.__init__(self, tube_class=GameTube, service=SERVICE)

	def _destroy_cb(self, data=None):
		return True

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
		session_data = json.write(self.ui._freeze())
		f = open(file_path, 'w')
		try:
			f.write(session_data)
		finally:
			f.close()
		#import urllib
		#logging.debug('Write session data: %s.' % urllib.quote(session_data))
