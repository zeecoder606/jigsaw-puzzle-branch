import os
import sys

cwd = os.path.split(__file__)[0]

import gtk
theme = gtk.icon_theme_get_default()

if os.path.exists(os.path.join(cwd, 'mmm_modules')):
    # We are self contained
    theme.append_search_path(os.path.join(cwd, 'mamamedia_icons'))
    pass
else:
    # Working with shared code on MaMaMediaMenu

    propfile = os.path.expanduser("~/.sugar/default/org.worldwideworkshop.olpc.MMMPath")
    if os.path.exists(propfile):
        mmmpath = file(propfile, 'rb').read()
    else:
        mmmpath=os.path.normpath(os.path.join(cwd, '..', 'MaMaMediaMenu.activity'))

    #print ("MMMPath", mmmpath)

    sys.path.append(mmmpath)
    theme.append_search_path(os.path.join(mmmpath, 'icons'))

from mmm_modules import *


if __name__ == '__main__':
    gather_other_translations()
    
