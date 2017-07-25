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
import tempfile
import random
import cairo
import os
import logging
logger = logging.getLogger('Jigsaw-puzzle')
import md5
from cStringIO import StringIO
from mmm_modules import BorderFrame, utils

MAGNET_POWER_PERCENT = 20
CUTTERS = {}

def create_pixmap (w, h):
    #cm = gtk.gdk.colormap_get_system()
    cairosurf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    drctx = cairo.Context(cairosurf)
    logger.debug('colormap1')
    #pm = gtk.gdk.Pixmap(None, w, h, cm.get_visual().depth)
    logger.debug('pixmap1')
    drctx.rectangle(0, 0, w, h)
    drctx.set_source_rgb(1.0, 1.0, 1.0)
    #gc = pm.new_gc()
    #gc.set_colormap(gtk.gdk.colormap_get_system())
    #color = cm.alloc_color('white')
    #gc.set_foreground(color)
    #pm.draw_rectangle(gc, True, 0, 0, w, h)
    drctx.fill()
    return drctx

class JigsawPiece (Gtk.EventBox):
    __gsignals__ = {'picked' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    'moved' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (int, int)),
                    'dropped' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),}
    
    def __init__ (self):
        super(JigsawPiece, self).__init__()
        self.index = None
        self.press_coords = (0,0)
        self.root_coords = (0,0)
        self.last_coords = (0,0)
        self.shape = None
        self.image = Gtk.Image()
        self.pb_wf = Gtk.Image()
        self.placed = False
        self._prepare_ui()
        self._prepare_event_callbacks()

    def _prepare_ui (self):
        self._c = Gtk.Fixed()
        self._c.show()
        self.add(self._c)
        self._c.put(self.image, 0, 0)
        self.image.show()
        self._c.put(self.pb_wf, 0, 0)

    def _prepare_event_callbacks (self):
        self.l_evids = []
        self.l_evids.append(self.connect('button-press-event', self._press_cb))
        self.l_evids.append(self.connect('button-release-event', self._release_cb))
        self.l_evids.append(self.connect('motion-notify-event', self._motion_cb))
        self.connect('draw', self._expose_cb)

    def set_index (self, index):
        self.index = index

    def get_index (self):
        return self.index
    
    def set_from_pixbuf(self, pb, pb_wf=None, mask=None):
        self.image.set_from_pixbuf(pb)
        self.width = pb.get_width()
        self.height = pb.get_height()
        self.shape = mask
        if pb_wf is not None:
            self.pb_wf.set_from_pixbuf(pb_wf)
            self.pb_wf.show()
            self.image.hide()
        self.set_size_request(self.width, self.height)

    def get_width (self):
        return self.width

    def get_height (self):
        return self.height

    def hide_wireframe (self):
        self.pb_wf.hide()
        self.image.show()

    def get_position (self):
        # The position relative to the puzzle playing area
        if self.get_parent and self.get_parent_window:
            bx,by,z5 = self.get_parent_window().get_origin()
            px,py,Z6 = self.get_window().get_origin()
            logger.debug('check it')
            logger.debug(bx)
            logger.debug(px)
            self.last_coords = (px-bx,py-by)
        return self.last_coords

    def set_position (self, x, y):
        # The new position, relative to the piece parent
        self.get_parent.move(self, x, y)

    def bring_to_top (self):
        p = self.get_parent()
        self.unparent()
        self.set_parent(p)

    def _press_cb (self, w, e, *attrs):
        self.press_coords = e.get_coords()
        self.root_coords = w.window.get_origin()
        self.emit('picked')
        
    def _motion_cb (self, w, e, *args):
        nx, ny = w.root_coords
        rx, ry = e.get_root_coords()
        px, py = w.press_coords
        delta = (rx-nx-px, ry-ny-py)
        w.root_coords = (nx+delta[0], ny+delta[1])
        self.emit('moved', *delta)

    def _release_cb (self, w, e, *args):
        self.emit('dropped')
        # The actual position in the whole window is w.window.get_origin()

    def _expose_cb (self, *args):
        if self.shape is not None:
            self.get_window.cairo_region_create_from_surface(self.shape, 0, 0)


class CutterBasic (object):
    """ Cutters are used to create the connectors between pieces.
    This one uses no connector at all, pieces will be simple rectangles. """
    SIDE_LEFT = 1
    SIDE_RIGHT = 2
    SIDE_TOP = 3
    SIDE_BOTTOM = 4

    connector_percent = 10

    def draw_connector (self, cairo_ctx, size, side, point_out=True, type=0):
        """
        cairo_ctx is the Cairo context used to draw, already at the start position for the connector.
        size is the length of the connector along the piece side. It's assumed to be 'connector_percent' of the side length.
        side describes the side being drawn.
        point_out is true if the connector is to be drawn onto the outside of the piece.
        type is a placeholder for supporting multiple connector subtypes.
        returns the extrusion size.
        """
        if side in (self.SIDE_RIGHT, self.SIDE_TOP):
            op = lambda x: -x
        else:
            op = lambda x: x

        if side in (self.SIDE_LEFT, self.SIDE_RIGHT):
            cairo_ctx.rel_line_to(0,op(size))
        else:
            cairo_ctx.rel_line_to(op(size),0)
        return 0
CUTTERS['basic'] = CutterBasic

class CutterSimple (CutterBasic):
    connector_percent = 20

    def draw_connector (self, cairo_ctx, size, side, point_out=True, type=0):
        if (side in (self.SIDE_RIGHT, self.SIDE_BOTTOM)) ^ point_out:
            op1 = lambda x: -x
        else:
            op1 = lambda x: x
        if side in (self.SIDE_RIGHT, self.SIDE_TOP):
            op2 = lambda x: -x
        else:
            op2 = lambda x: x
            
        if side in (self.SIDE_LEFT, self.SIDE_RIGHT):
            cairo_ctx.rel_line_to(op1(size),0)
            cairo_ctx.rel_line_to(0,op2(size))
            cairo_ctx.rel_line_to(-op1(size),0)
        else:
            cairo_ctx.rel_line_to(0,op1(size))
            cairo_ctx.rel_line_to(op2(size),0)
            cairo_ctx.rel_line_to(0,-op1(size))
        return size
CUTTERS['simple'] = CutterSimple

class CutterClassic (CutterBasic):
    connector_percent = 20

    def draw_connector (self, cairo_ctx, size, side, point_out=True, type=0):
        if (side in (self.SIDE_RIGHT, self.SIDE_BOTTOM)) ^ point_out:
            op1 = lambda x: -x
        else:
            op1 = lambda x: x
        if side in (self.SIDE_RIGHT, self.SIDE_TOP):
            op2 = lambda x: -x
        else:
            op2 = lambda x: x
            
        if side in (self.SIDE_LEFT, self.SIDE_RIGHT):
            cairo_ctx.rel_curve_to(op1(size*2), -op2(size*1.5), op1(size*2), op2(size*2.5), 0, op2(size))
        else:
            cairo_ctx.rel_curve_to(-op2(size*1.5), op1(size*2), op2(size*2.5), op1(size*2), op2(size), 0)
        return size*2
CUTTERS['classic'] = CutterClassic

class CutBoard (object):
    def __init__ (self, *args, **kwargs):
        if len(args) or len(kwargs):
            self._prepare(*args, **kwargs)
        self.cutter = CutterClassic()
        self.pb = None
        self.cols = None
        self.rows = None
        self.h_connector_hints = None
        self.v_connector_hints = None
        self.image = None

    def _prepare (self, cols, rows, cutter=None, hch=None, vch=None):
        if self.pb is None:
            logging.error("You must fist set CutBoard.pb with a pixbuf to be used!")
            return
        if cutter is not None:
            self.cutter = CUTTERS.get(cutter, CutterClassic)()
        self.rows = rows
        self.cols = cols
        if hch is not None:
            self.h_connector_hints = hch
        else:
            self.h_connector_hints = [random.random()*2-1 for x in range((self.rows+1)*(self.cols+1))]
        if vch is not None:
            self.v_connector_hints = vch
        else:
            self.v_connector_hints = [random.random()*2-1 for x in range((self.rows+1)*(self.cols+1))]
        self.width, self.height = self.pb.get_width(), self.pb.get_height()
        self.pm = create_pixmap(self.width, self.height)
        self.cr = self.pm
        #self.cr = Gdk.CairoContext(self.cr)
        self.pieces = []
        self.prepare_hint()
        for c in range(self.cols):
            self.pieces.append([])
            for r in range(self.rows):
                self.pieces[c].append(self.cut(c,r))

    def get_cutter (self):
        for k,v in CUTTERS.items():
            if isinstance(self.cutter, v):
                return k
        return None

    def set_cutter (self, cutter):
        if cutter is not None:
            self.cutter = CUTTERS.get(cutter, CutterClassic)()

    def prepare_hint (self):
        self.hint_pm = create_pixmap(self.width, self.height)
        self.hint_cr = self.hint_pm
        self.hint_cr.set_source_rgb (0,0,0)
        self.hint_cr.set_line_width(0.5)

    def refresh (self):
        #self.cr.set_source_pixbuf(self.pb, 0, 0)
        Gdk.cairo_set_source_pixbuf(self.cr, self.pb, 0, 0)
        self.cr.paint()
        self.cr.set_line_width(1.0)
        self.cr.set_source_rgb(0,0,0)

    def get_hint (self):
        pb = Gdk.pixbuf_get_from_surface(self.hint_pm.get_target(), 0, 0, self.width, self.height)
        #pb.get_from_surface(self.hint_pm.get_target(), 0, 0, self.width, self.height)
        return pb

    def draw_vertical_path (self, cairo_ctx, piece_nr, col, height, ptype=0):
        """ returns the number of overlapping pixels on the drawn side """
        if col > piece_nr:
            # right_side
            op = lambda x: -x
        else:
            # left_side
            op = lambda x: x
        if col > 0 and col < self.cols:
            point_out = col > piece_nr
            t1 = height*self.cutter.connector_percent/100.0
            t2 = t1/2.0
            if ptype < 0:
                point_out = not point_out
            cairo_ctx.rel_line_to(0, op((height/2.0) - t2))
            t = self.cutter.draw_connector(cairo_ctx, t1, col>piece_nr and self.cutter.SIDE_RIGHT or self.cutter.SIDE_LEFT, point_out)
            cairo_ctx.rel_line_to(0, op((height/2.0) - t2))
            if point_out:
                overlap = t
            else:
                overlap = 0
        else:
            cairo_ctx.rel_line_to(0, op(height))
            overlap = 0
        return overlap

    def draw_horizontal_path (self, cairo_ctx, piece_nr, row, width, ptype=0):
        """ returns the number of overlapping pixels on the drawn side """
        # positive or negative connector? We must randomize this.
        if row > piece_nr:
            # bottom_side
            op = lambda x: x
        else:
            # top_side
            op = lambda x: -x
        if row > 0 and row < self.rows:
            point_out = row > piece_nr
            t1 = width*self.cutter.connector_percent/100.0
            t2 = t1/2.0
            if ptype < 0:
                point_out = not point_out
            cairo_ctx.rel_line_to(op((width/2.0) - t2), 0)
            t = self.cutter.draw_connector(cairo_ctx, t1, row>piece_nr and self.cutter.SIDE_BOTTOM or self.cutter.SIDE_TOP, point_out)
            cairo_ctx.rel_line_to(op((width/2.0) - t2), 0)
            if point_out:
                overlap = t
            else:
                overlap = 0
        else:
            cairo_ctx.rel_line_to(op(width),0)
            overlap = 0
        return overlap

    def path_for_piece (self, cairo_context, x, y, width, height):
        hpos = (y*self.cols)+x
        vpos = (x*self.rows)+y
        l_offset = self.draw_vertical_path(cairo_context, x, x, height, self.h_connector_hints[hpos])
        b_offset = self.draw_horizontal_path(cairo_context, y, y+1, width, self.v_connector_hints[vpos+1])
        r_offset = self.draw_vertical_path(cairo_context, x, x+1, height, self.h_connector_hints[hpos+1])
        t_offset = self.draw_horizontal_path(cairo_context, y, y, width, self.v_connector_hints[vpos])
        return {'left':l_offset, 'right': r_offset, 'top': t_offset, 'bottom': b_offset}

    def cut (self, x, y):
        width = self.width / self.cols
        height = self.height / self.rows
        px = width*x
        py = height*y
        if x == self.cols - 1:
            width = self.width - px
        if y == self.rows - 1:
            height = self.height - py

        # the cut mask is done on each piece at the right and bottom sides,
        # except for the right on the last column and bottom on the last row.

        # Draw outline on the board hint image
        self.hint_cr.move_to(px,py)
        offsets = self.path_for_piece(self.hint_cr, x, y, width, height)
        self.hint_cr.stroke()

        width_offset = int(offsets['left'] + offsets['right'])
        height_offset = int(offsets['top'] + offsets['bottom'])
        width = int(width)
        height = int(height)
        # Prepare the piece mask
        mask_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width+width_offset, height+height_offset)
        #gtk.gdk.Pixmap(None, width+width_offset, height+height_offset, 1)
        mask_cr = cairo.Context(mask_surface)
        mask_cr.save()
        mask_cr.set_operator(cairo.OPERATOR_SOURCE)
        mask_cr.set_source_rgba(0,0,0,0)
        mask_cr.paint()
        mask_cr.restore()
        mask_cr.set_line_width(1.0)
        mask_cr.set_source_rgba(1,1,1,1)
        mask_cr.move_to(offsets['left'], offsets['top'])
        self.path_for_piece(mask_cr, x, y, width, height)
        mask_cr.stroke_preserve()
        mask_cr.fill()

        width += width_offset
        height += height_offset
        px -= int(offsets['left'])
        py -= int(offsets['top'])

        # The piece image
        self.refresh()
        #pb = GdkPixbuf.Pixbuf(GdkPixbuf.Colorspace.RGB, True, 8, width, height)
        #pb.get_from_drawable(self.pm, self.pm.get_colormap(), px, py, 0, 0, width, height)
        pb = Gdk.pixbuf_get_from_surface(self.pm.get_target(), 0, 0, self.width, self.height)
        # The outlined image
        self.cr.move_to(px+offsets['left'], py+offsets['top'])
        self.path_for_piece(self.cr, x, y, width-width_offset, height-height_offset)
        self.cr.stroke()
        #pb_wf = GdkPixbuf.Pixbuf(GdkPixbuf.Colorspace.RGB, True, 8, width, height)
        #pb_wf.get_from_drawable(self.pm, self.pm.get_colormap(), px, py, 0, 0, width, height)
        pb_wf = Gdk.pixbuf_get_from_surface(self.pm.get_target(), 0, 0, self.width, self.height)
        return (pb, pb_wf, mask_surface, px, py, width-width_offset, height-height_offset)


    def get_image_as_png(self, cb=None):
        if self.image is None:
            return None
        # save_to_streamv is missing entirely,
        # save_to_bufferv appears to be unusable,
        # and it looks like save_to_callback's data is being truncated on NULL.
        # Check http://ubuntuforums.org/showthread.php?t=1877793
        # XXX: Hack
        tmp_file = tempfile.NamedTemporaryFile()
        tmp_file_name = tmp_file.name
        self.image.savev(tmp_file_name, "png", [], [])
        pb_s = GdkPixbuf.Pixbuf.new_from_file(tmp_file_name).to_string()
        tmp_file.close()
        return pb_s
    

    def _freeze (self, img_cksum_only=False):
        if self.pb is not None:
            if img_cksum_only:
                cksum = md5.new()
                self.get_image_as_png(cksum.update)
                return {'geom': (self.cols, self.rows),
                        'hints': (self.h_connector_hints, self.v_connector_hints),
                        'pb-cksum': cksum.hexdigest(),
                        'cutter': self.get_cutter(),
                        }
            else:
                return {'geom': (self.cols, self.rows),
                        'hints': (self.h_connector_hints, self.v_connector_hints),
                        'pb': self.get_image_as_png(),
                        'cutter': self.get_cutter(),
                        }
        return None

    def _thaw (self, data):
        if data is None:
            return
        if data.has_key('pb') and data['pb'] is not None:
            fn = os.tempnam() 
            f = file(fn, 'w+b')
            f.write(data['pb'])
            f.close()
            i = Gtk.Image()
            i.set_from_file(fn)
            os.remove(fn)
            self.pb = i.get_pixbuf()
            del data['pb']
        logging.debug("cutboard._thaw(%s)" % str(data))
        cols, rows = data['geom']
        hch, vch = data['hints']
        cutter = data['cutter']
        self._prepare(cols, rows, cutter, hch, vch)


class JigsawBoard (BorderFrame):
    """ Drop area for jigsaw pieces to be tested against.
    Maybe use this to do the piece cutting / hint ? """
    __gsignals__ = {'solved' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
                    }
    def __init__ (self):
        super(JigsawBoard, self).__init__(border_color="#0000FF")
        #self.image = None
        self.board = Gtk.Fixed()
        self.board.show()
        self.add(self.board)
        self.board_distribution = None
        self.target_pieces_per_line = 3
        self.hint_board_image = Gtk.Image()
        self.cutboard = CutBoard()

    def get_cutter (self):
        return self.cutboard.get_cutter()

    def set_cutter (self, cutter):
        self.cutboard.set_cutter(cutter)
        
    def update_hint (self):
        self.hint_board_image.set_from_pixmap(self.hint_board, None)

    def set_image (self, pixbuf):
        self.board.foreach(self.board.remove, None)
        self.board_distribution = None
        self.board.put(self.hint_board_image, 0,0)
        self.img_width = pixbuf.get_width()
        self.img_height = pixbuf.get_height()
        self.set_size_request(self.img_width, self.img_height)
        self.queue_resize()
        self.cutboard.pb = pixbuf

    #def reshuffle (self):
    #    self.cutboard._prepare(self.target_pieces_per_line,self.target_pieces_per_line)#, self.cutter)

    def get_pieces (self, reshuffle=True):
        if self.cutboard.pb is None:
            return
        self.board_distribution = []
        pcw = self.target_pieces_per_line
        pch = self.target_pieces_per_line
        # Find the best cut for our difficulty level
        changed = True
        while changed:
            pw = self.img_width / pcw
            ph = self.img_height / pch
            changed = False
            if pcw == 1 or pch == 1:
                break
            if abs((self.img_width / (pcw-1))-ph) < abs(pw-ph):
                pcw -= 1
                changed = True
                continue
            if abs((self.img_height / (pch-1))-pw) < abs(ph-pw):
                pch -= 1
                changed = True

        logging.debug("Board matrix %s %s" % (pcw, pch))
        if reshuffle:
            self.cutboard._prepare(pcw, pch)
        # Prepare the pieces
        self.hint_board_image.set_from_pixbuf(self.cutboard.get_hint())

        pos_x = 0
        for col in range(pcw):
            pos_y = 0
            for row in range(pch):
                piece = JigsawPiece()
                pb, pb_wf, mask, px, py, pw, ph = self.cutboard.pieces[col][row]
                piece.set_from_pixbuf(pb, pb_wf, mask)
                piece.show()
                piece.set_index(len(self.board_distribution))
                self.board_distribution.append((px, py, pw*MAGNET_POWER_PERCENT/100.0, ph*MAGNET_POWER_PERCENT/100.0))
                yield piece

    def get_placed_pieces (self):
        return [x for x in self.board.get_children() if isinstance(x, JigsawPiece)]

    def place_piece (self, piece):
        piece.placed = True
        index = piece.get_index()
        piece.reparent(self.board)
        #piece.hide_wireframe()
        bx, by, mx, my = self.board_distribution[index]
        self.board.move(piece, bx, by)
        self.board_distribution[index] = None
        if len(filter(None, self.board_distribution))==0:
            for p in self.board.get_children():
                if isinstance(p, JigsawPiece):
                    p.hide_wireframe()
            self.emit('solved')

    def drop_piece (self, piece, x, y):
        index = piece.get_index()
        bx, by, mx, my = self.board_distribution[index]
        x -= self.padding[0]
        y -= self.padding[1]
        logging.debug("Board drop for piece #%i (%i,%i) : (%i,%i)" % (index, x,y,bx,by))
        if abs(bx-x) < mx and abs(by-y) < my:
            # We have a positive positioning
            self.place_piece(piece)

    def _freeze (self, img_cksum_only=False):
        return {'target_pieces_per_line': self.target_pieces_per_line,
                'cutboard': self.cutboard and self.cutboard._freeze(img_cksum_only) or None,
                }

    def _thaw (self, data):
        for k in ('target_pieces_per_line', ):
            if data.has_key(k):
                setattr(self, k, data[k])
        self.cutboard._thaw(data['cutboard'])
            

class JigsawPuzzleWidget (Gtk.EventBox):
    __gsignals__ = {
        'picked' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (JigsawPiece,)),
        'dropped' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (JigsawPiece,bool)),
        'solved' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, ()),
        'cutter-changed' : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (str, int)),
        }
    def __init__ (self):
        super(JigsawPuzzleWidget, self).__init__()
        self._container = Gtk.Fixed()
        self.add(self._container)
        self.board = JigsawBoard()
        self.board.connect('solved', self._solved_cb)
        self.board.show()
        self._container.put(self.board, 10, 10)
        self._container.show_all()
        self.running = False
        self.forced_location = False

    def bring_to_top (self, piece):
        wx, wy = self._container.child_get_property(piece, 'x', 'y')
        
        self._container.remove(piece)
        self._container.put(piece, wx, wy)

    def show_hint (self, show):
        if show:
            self.board.hint_board_image.show()
        else:
            self.board.hint_board_image.hide()

    def get_floating_pieces (self):
        return [x for x in self._container.get_children() if isinstance(x, JigsawPiece)]

    def set_cutter (self, cutter):
        if cutter is None:
            cutter = 'classic'
            logging.debug('set_cutter(None) setting default to "classic"')
        self.board.set_cutter(cutter)
        self.emit('cutter-changed', self.get_cutter(), self.board.target_pieces_per_line)

    def get_cutter (self):
        return self.board.get_cutter()

    def set_target_pieces_per_line (self, tppl):
        if tppl is None:
            tppl = 3
        self.board.target_pieces_per_line = tppl
        self.emit('cutter-changed', self.get_cutter(), self.board.target_pieces_per_line)

    def get_target_pieces_per_line (self):
        return self.board.target_pieces_per_line

    def prepare_image (self, pixbuf=None, reshuffle=True):
        allocation = self.get_allocation()
        x = allocation.x
        y = allocation.y
        w = allocation.width
        h = allocation.height
        if pixbuf is not None:
            factor = min((float(w)*0.6)/pixbuf.get_width(), (float(h)*0.6)/pixbuf.get_height())
            pixbuf = pixbuf.scale_simple(int(pixbuf.get_width() * factor),
                                         int(pixbuf.get_height()*factor),
                                         GdkPixbuf.InterpType.BILINEAR)
        if pixbuf is None:
            pixbuf = self.board.cutboard.pb
        if pixbuf is None:
            return False
        self.board.set_image(pixbuf)

        for child in self._container.get_children():
            if child is not self.board:
                self._container.remove(child)
        bx, by = self._container.child_get(self.board, 'x', 'y')
        
        logger.debug('child here')
        logger.debug(bx)
        logger.debug(by)
        #bx = 10
        #by = 10
        bw, bh = self.board.inner.get_size_request()
        #br = Gdk.Rectangle(bx,by,bw,bh)
        br = Gdk.Rectangle()
        br.x = bx
        br.y = by
        br.width = bw
        br.height = bh
        for n, piece in enumerate(self.board.get_pieces(reshuffle)):
            if self.forced_location and len(self.forced_location)>n:
                if self.forced_location[n] is None:
                    # Will be placed in the correct place later
                    self._container.put(piece, 0, 0)
                else:
                    self._container.put(piece, *self.forced_location[n])
            else:
                pw,ph = piece.get_size_request()
                r = Gdk.Rectangle()
                r.x = bx
                r.y = by
                r.width = pw
                r.height = ph

                r.x = int(random.random()*(w-pw))
                r.y = int(random.random()*(h-ph))
                #if br.intersect(r).width > 0:
                #    r.x = int(random.random()*(w-pw))
                #    r.y = int(random.random()*(h-ph))
                self._container.put(piece, r.x, r.y)
            piece.connect('picked', self._pick_cb)
            piece.connect('moved', self._move_cb)
            piece.connect('dropped', self._drop_cb)
            if self.forced_location and len(self.forced_location)>n and self.forced_location[n] is None:
                self.board.place_piece(piece)
            while Gtk.events_pending():
                Gtk.main_iteration()
            piece.get_position()
        self.forced_location = None
        self.running = True
        return True

    def is_running (self):
        return self.running

    def solve (self):
        for p in [x for x in self._container.get_children() if isinstance(x, JigsawPiece)]:
            self.board.place_piece(p)

    def _solved_cb (self, *args):
        self.emit('solved')

    def _pick_cb (self, w):
        self.emit('picked', w)

    def _move_cb (self, w, x, y, absolute=False):
        if w.get_parent() != self._container:
            return
        if absolute:
            wx,wy = 0,0
        else:
            wx, wy = self._container.child_get_property(w, 'x', 'y')
            

        wa = w.get_allocation()
        x1 = wa.x
        y1 = wa.y
        w1 = wa.width
        z1 = wa.height

        ca = self._container.get_allocation()
        x2 = ca.x
        y2 = ca.y
        w2 = ca.width
        z2 = ca.height


        if wx+x > 0 and wy+y > 0 and wx+w1+x <= w2 \
                and wy+z1+y <= z2:
            #logging.debug("moving %i,%i : %i:%i : %i:%i" % (wx,wy, x, y,wx+x, wy+y))
            self._container.move(w, max(0,wx+x), max(0,wy+y))

    def _drop_cb (self, w, from_mesh=False):
        if w.get_parent() != self._container:
            return
        self.bring_to_top(w)
        allocation1 = w.get_allocation()
        x = allocation1.x
        y = allocation1.y
        a = allocation1.width
        b = allocation1.height
        #x,y,a,b = w.get_allocation()
        c,d = w.get_size_request()
        logging.debug("Dropped Widget allocation: %s %s %s %s %s %s" % (x,y,a,b,c,d))
        if w.intersect(self.board.get_allocation()):
            allocation2 = w.get_allocation()
            wx = allocation2.x
            wy = allocation2.y
            ww = allocation2.width
            wh = allocation2.height

            allocation3 = self.board.get_allocation()
            bx = allocation2.x
            by = allocation2.y
            bw = allocation2.width
            bh = allocation2.height

            self.board.drop_piece(w, wx-bx, wy-by)
        self.emit('dropped', w, from_mesh)
        
    def _debug_cb (self, w, e, *args):
        logging.debug("%s %s %s" % (w, e, args))

    def _freeze (self, img_cksum_only=False):
        pieces = [(x.get_index(), None) for x in self.board.get_placed_pieces()]
        
        pieces.extend([(x.get_index(), x.get_position()) for x in self.get_floating_pieces()])
        pieces.sort(key=lambda x: x[0])
        return {'board': self.board._freeze(img_cksum_only),
                'cutter': self.get_cutter(),
                'target_pieces_per_line': self.get_target_pieces_per_line(),
                'piece_pos': [x[1] for x in pieces]}

    def _thaw (self, data):
        if data.has_key('board'):
            self.board._thaw(data['board'])
        self.set_cutter(data.get('cutter', None))
        self.set_target_pieces_per_line(data.get('target_pieces_per_line', None))
        self.forced_location = data.get('piece_pos', None)
        
if __name__ == '__main__':
    w = Gtk.Window()
    j = JigsawPuzzleWidget()
    img = utils.load_image('test_image.gif')
    
    j.prepare_image(img)
    
    w.add(j)
    w.show_all()
    Gtk.main()
