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
    # Set the zetas to be all one and set alpha to 2
    alpha = 2
    zeta = 1

    N = data.shape[0]
    d = data.shape[1]

