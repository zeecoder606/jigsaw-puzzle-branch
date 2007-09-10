import os
import sys

propfile = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.MMMPath")
if os.path.exists(propfile):
    mmmpath = file(propfile, 'rb').read()
else:
    mmmpath=os.path.normpath(os.path.join(os.path.split(__file__)[0], '..', 'MaMaMediaMenu.activity'))

print ("MMMPath", mmmpath)

sys.path.append(mmmpath)

from mmm_modules import *

import gtk
theme = gtk.icon_theme_get_default()
theme.append_search_path(os.path.join(mmmpath, 'icons'))

if __name__ == '__main__':
    gather_other_translations()
    
