import pandas as pd
import numpy as np
from . import pyvistawrapper

def dump(tri, filename, **kw):
    pyvistawrapper.to_pyvista(tri, **kw).save(filename)
