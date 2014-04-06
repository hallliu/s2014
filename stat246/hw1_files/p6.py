#!/usr/bin/python2
import numpy as np
import scipy.stats as st
import pyximport
pyximport.install()
from helper_fns import *

'''
Computes the e and m arrays as desired. e is returned
as a d by d by 1000 array. A is the component of the 
covariance matrix.
'''
def compute_results(d, A):
    iters = 1000
    n_samples = 500

    e_data = np.zeros((iters, d, d))
    m_data = np.zeros(iters)

    for t in range(iters):
        # Perform the random sample
        samples = np.random.randn(d, n_samples)
        # Transform it to have the correct distribution
        samples = np.dot(A.T, samples)

        # Compute the covariance estimation
        cov_est = np.dot(samples, samples.T) / n_samples

        # Compute the standardized errors
        stderrs = compute_stderrs(np.dot(A.T, A), n)
        e_data[t, :, :] = (cov - cov_est) / stderrs
        m_data[t] = np.min(np.linalg.eigvalsh(cov_est))

    return (e_data, m_data)
