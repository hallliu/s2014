#!/usr/bin/python2
import numpy as np
import scipy.stats as st
import matplotlib.pyplot as plt
from helper_fns import *

'''
Computes the e and m arrays as desired. e is returned
as a d by d by 1000 array. A is the component of the 
covariance matrix.
'''
def compute_results(d, A, n_samples):
    iters = 1000

    e_data = np.zeros((iters, d, d))
    m_data = np.zeros(iters)
    cov = np.dot(A.T, A)

    for t in range(iters):
        # Perform the random sample
        samples = np.random.randn(d, n_samples)
        # Transform it to have the correct distribution
        samples = np.dot(A.T, samples)

        # Compute the covariance estimation
        cov_est = np.dot(samples, samples.T) / n_samples

        # Compute the standardized errors
        stderrs = compute_stderrs(cov, n_samples)
        e_data[t, :, :] = (cov - cov_est) / stderrs
        m_data[t] = np.min(np.linalg.eigvalsh(cov_est))

    return (e_data, m_data)

def generate_results():
    a100 = np.loadtxt('./a100.txt')
    a10 = np.loadtxt('./a10.txt')

    for ssize in [500, 5000]:
        e10_data, m10_data = compute_results(10, a10, ssize)
        e100_data, m100_data = compute_results(100, a100, ssize)
        e10f = e10_data.flatten()
        e100f = e100_data.flatten()

        print('10 mean: {0}. 100 mean: {1}'.format(e10f.mean(), e100f.mean()))
        print('10 std: {0}. 100 std: {1}'.format(e10f.std(), e100f.std()))

        plt.figure()
        hist10, bins10 = np.histogram(e10f, bins=50)
        width10 = 0.6*(bins10[1] - bins10[0])
        centers10 = (bins10[:-1] + bins10[1:]) / 2
        plt.bar(centers10, hist10, align='center', width=width10)
        plt.savefig('e10-{0}.png'.format(ssize), bbox_inches='tight')

        plt.figure()
        hist100, bins100 = np.histogram(e100f, bins=50)
        width100 = 0.6*(bins100[1] - bins100[0])
        centers100 = (bins100[:-1] + bins100[1:]) / 2
        plt.bar(centers100, hist100, align='center', width=width100)
        plt.savefig('e100-{0}.png'.format(ssize), bbox_inches='tight')

generate_results()
