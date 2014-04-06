import numpy as np
cimport numpy as np
cimport cython

@cython.boundscheck(False)
def compute_stderrs(np.ndarray[double, ndim=2] cov, int n):
    cdef int i, j
    cdef int d = cov.shape[0]
    cdef np.ndarray[double, ndim=2] cov_stderrs = np.zeros((d, d), dtype='float64')
    for i in range(d):
        for j in range(d):
            cov_stderrs[i, j] = cov[i, i]*cov[j, j] + cov[i, j] * cov[i, j]
    cov_stderrs /= n
    return cov_stderrs

