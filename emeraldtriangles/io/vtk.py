import pandas as pd
import numpy as np
from . import pyvista

def dump(tri, filename, **kw):
    pyvista.to_pyvista(tri, **kw).save(filename)
