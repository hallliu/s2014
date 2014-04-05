#!/usr/bin/python2
import numpy as np
import scipy.stats as st

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
        stderr_array = e_data[t, :, :]


