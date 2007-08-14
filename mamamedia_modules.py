import os
import sys

propfile = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.MMMPath")
mmmpath = file(propfile, 'rb').read()
sys.path.append(mmmpath)

from mmm_modules import *

import gtk
theme = gtk.icon_theme_get_default()
theme.append_search_path(os.path.join(mmmpath, 'icons'))

if __name__ == '__main__':
    gather_other_translations()
    
