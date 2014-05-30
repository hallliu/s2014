import numpy as np
import scipy.linalg as sp

def run_gibbs_normal(n_samp, epsilon):
    r1 = np.array([2+epsilon, -1, 0, -1])
    Q = sp.circulant(r1)
    prec = Q
    samples = np.zeros((4, n_samp), dtype='float64')
    running_sample = np.zeros(4, dtype='float64')

    # Precompute 40k std normal samples
    std_normal_samples = np.random.randn(4*n_samp)
    
    # Run 10000 iterations over all 4 coordinates
    for i in range(n_samp):
        for j in range(4):
            mean = np.dot(prec[j], running_sample) - prec[j, j]*running_sample[j]
            mean /= prec[j, j]
            std = np.sqrt(1/prec[j, j])
            running_sample[j] = std_normal_samples[i*4+j] * std + mean
        samples[:, i] = running_sample

    return samples

def est_covs(samples):
    c1 = samples[:1000].copy()
    cf = samples[-1000:].copy()
    c1 -= c1.mean(0)
    cf -= cf.mean(0)
    samples -= samples.mean(0)

    return np.dot(c1,c1.T)/999, np.dot(c2,c2.T)/999, np.dot(samples, sample.T)/9999

def main(epsilon):
    f1000_rhos = np.zeros(100)
    l1000_rhos = np.zeros(100)
    total_rhos = np.zeros(100)

    r1 = np.array([2+epsilon, -1, 0, -1])
    Q = sp.circulant(r1)
