import pandas as pd
import numpy as np
from . import surface
from . import volume

def dump(tri, filename=None, layer_depths=None, **kw):
    """Dumps a surface based on your triangles. If layer_depths is
       specified the TIN is interpreted as a 2.5d volume, and
       triangular prisms are generated, with heights from the
       layer_depths list.
       You can override the columns used for coordinates:
       x_col="X", y_col="Y", z_col="Z"
    """
    if layer_depths is not None:
        poly = volume.to_pyvista(tri, layer_depths=layer_depths, **kw)
    else:
        poly = surface.to_pyvista(tri, **kw)
    if filename is not None:
        poly.save(filename)
    return poly
