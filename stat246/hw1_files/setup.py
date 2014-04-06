from distutils.core import setup
from Cython.Distutils import build_ext, Extension
import numpy as np

setup(
    cmdclass = {'build_ext': build_ext},
    ext_modules = [Extension("helper_fns", ['helper_fns.pyx'], extra_compile_args=['-O3', '-std=gnu99'])],
    include_dirs=[np.get_include()]
)
