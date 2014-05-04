import numpy as np

'''
Returns a 10 by N by 900 array. Digit classes on the first axis, individual cases
on the second. N=100 for train, 1000 for test
'''
def load_digits(case='tr'):
    if case == 'tr':
        N = 100
    else:
        N = 1000
    digits = np.zeros((10, N, 900), dtype='int8')
    for i in range(10):
        c = np.fromfile('{0}{1}.bin'.format(case, i), dtype='int8')
        digits[i] = c.reshape(N, 900)

    return digits

'''
Takes a N by 900 matrix (each row is a data vector), and trains EM on it.
'''
def em_map(data, M):
    # Set the zetas to be all 2 and set alpha to 2
    alpha = 2
    zeta = 2

    N = data.shape[0]
    d = data.shape[1]
    # In lieu of randomly assigning classes, we'll just assign the classes by taking
    # the data point index mod M. Note that assigning a class to a point i is equivalent to setting
    # w_{i,m}=1 for the assigned class m and zero for all other classes.
    cond_probs = np.zeros((N, M), dtype='float64')
    pis = np.zeros(M, dtype='float64')
    bern_probs = np.zeros((d, M), dtype='float64')
    for i in range(N):
        cond_probs[i,i%M] = 1

    pis, bern_probs = calc_params(data, cond_probs, alpha, zeta)

    while True:
        cond_probs = calc_cond_probs(data, pis, bern_probs)
        new_pis, new_bern_probs = calc_params(data, cond_probs, alpha, zeta)
        m1 = np.linalg.norm(new_pis - pis)
        m2 = np.linalg.norm(new_bern_probs - bern_probs)
        if m1 < epsilon and m2 < epsilon:
            return new_pis, new_bern_probs
        print m2
        pis = new_pis
        bern_probs = new_bern_probs

'''
Calculates parameters given the data and the W matrix, along with some priors.
Returns the new pis and bernoulli params
'''
def calc_params(data, W, alpha, zeta):
    N = data.shape[0]
    pis = W.sum(0) + zeta - 1
    pis /= pis.sum()

    p_numer = np.dot(data.T + (alpha-1)/N, W)
    p_denom = W.sum(0)*(2*(alpha-1)/N + 1)

    bern_probs = p_numer / p_denom
    return pis, bern_probs

'''
Calculates the matrix of conditional probabilities of given
parameters.
'''
def calc_cond_probs(data, pis, bern_probs):
    M = pis.shape[0]
    N = data.shape[0]
    weights = np.zeros((N,M), dtype='float64')

    log_joints = np.dot(data.T, np.log(bern_probs)) + np.dot((1-data).T, np.log(1-bern_probs))
    # fugly hack that exploits a numpy bug
    try:
        log_joints.T += np.log(pis)
    except:
        pass

    max_logs = np.amax(log_joints, axis=1)
    try:
        log_joints.T -= max_logs
    except:
        pass

    weights = np.exp(log_joints)
    try:
        weights.T /= weights.sum(1)
    except:
        pass

    return weights
