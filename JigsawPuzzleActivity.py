from sugar.activity.activity import Activity, ActivityToolbox, get_bundle_path
from gettext import gettext as _
import logging, os, sys

from JigsawPuzzleUI import JigsawPuzzleUI

logger = logging.getLogger('jigsawpuzzle-activity')

class JigsawPuzzleActivity(Activity):
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

	def _destroy_cb(self, data=None):
		return True
