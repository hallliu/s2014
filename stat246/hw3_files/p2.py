import numpy as np
import scipy.stats as st
'''
data is a N by d matrix; each row is an observation
'''
def poisson_em(data, epsilon, pis=None, thetas=None):
    N, d = data.shape
    if pis is None:
        pis = np.random.rand(d)
        pis /= pis.sum()
    if thetas is None:
        thetas = np.random.rand(d) * 2

    while True:
        weight_matrix = compute_weights(data, thetas, pis)

        new_pis = weight_matrix.sum(0) / N

        new_thetas = np.zeros(d)
        for j in range(d):
            data_permuted = np.roll(data, -j, axis=1)
            new_thetas[j] = (weight_matrix * data_permuted).sum() / N 

        if np.linalg.norm(new_pis - pis) < epsilon and np.linalg.norm(new_thetas - thetas) < epsilon:
            return (thetas, pis)

        print np.linalg.norm(new_thetas - thetas)
        pis = new_pis
        thetas = new_thetas

'''
Returns the weights in the same shape as data
'''
def compute_weights(data, theta, pis):
    N, d = data.shape
    p_fn = st.poisson(theta).pmf

    weights = np.zeros((N, d))
    for m in range(d):
        data_permuted = np.roll(data, -m, axis=1)
        for n in range(N):
            weights[n, m] = np.log(p_fn(data_permuted[n])).sum() + np.log(pis[m])

    max_alphas = np.amax(weights, axis=1)
    weights -= max_alphas[:, np.newaxis]
    weights = np.exp(weights)
    w_sums = weights.sum(1)
    weights /= w_sums[:, np.newaxis]
    return weights
