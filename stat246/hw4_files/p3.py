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
def em_map(data, M, epsilon=1e-5):
    # Set the zetas to be all 2 and set alpha to 2
    alpha = 2.0
    zeta = 2.0

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

    log_joints = np.dot(data, np.log(bern_probs)) + np.dot((1-data), np.log(1-bern_probs))
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

'''
Runs the model for all 10 digits, on M=1,3,5, plots the components, and returns
the parameters.
'''
def train_on_digits():
    import matplotlib.pyplot as plt
    train_set = load_digits('tr')

    pis_1 = []
    probs_1 = []
    plt.figure(figsize=(8,3))
    for i in range(10):
        plt.subplot(2, 5, i+1)
        plt.axis('off')
        pis, probs = em_map(train_set[i], 1)
        plt.imshow(probs[:,0].reshape(30, 30), cmap=plt.cm.Greys)
        pis_1.append(pis)
        probs_1.append(probs)
    #plt.savefig('M1_princip.png', bbox_inches='tight')

    pis_3 = []
    probs_3 = []
    plt.figure(figsize=(8.5,3))
    for i in range(10):
        pis, probs = em_map(train_set[i], 3)
        for j in range(3):
            plt.subplot(3, 10, j*10+i+1)
            plt.axis('off')
            plt.imshow(probs[:,j].reshape(30, 30), cmap=plt.cm.Greys)
        pis_3.append(pis)
        probs_3.append(probs)
    #plt.savefig('M3_princip.png', bbox_inches='tight')

    pis_5 = []
    probs_5 = []
    plt.figure(figsize=(8.5,5))
    for i in range(10):
        pis, probs = em_map(train_set[i], 5)
        for j in range(5):
            plt.subplot(5, 10, j*10+i+1)
            plt.axis('off')
            plt.imshow(probs[:,j].reshape(30, 30), cmap=plt.cm.Greys)
        pis_5.append(pis)
        probs_5.append(probs)
    #plt.savefig('M5_princip.png', bbox_inches='tight')

    pis_1 = np.vstack(pis_1)
    pis_3 = np.vstack(pis_3)
    pis_5 = np.vstack(pis_5)

    return ((pis_1, probs_1), (pis_3, probs_3), (pis_5, probs_5))

'''
Loads the test files and classifies them using argmax of likelihoods, and proceeds
to compute the error rates for M=1,3,5
'''
def perform_classifications(learned_params):
    test_data = load_digits('te')
    for (i, M) in enumerate([1,3,5]):
        pis = learned_params[i][0]
        probs = learned_params[i][1]
        error_count = 0
        # Loop through the test classes
        for j in range(10):
            class_data = test_data[j]
            likelihoods_by_class = np.zeros((1000, 10))
            # Loop through the trained classes to evaluate likelihoods
            for k in range(10):
                log_likelihoods = np.dot(class_data, np.log(probs[k])) + np.dot(1-class_data, np.log(1-probs[k]))
                likelihoods_by_class[:, k] = (np.exp(log_likelihoods) * pis[k]).sum(1)
            predicted_classes = np.argmax(likelihoods_by_class, 1)
            error_count += np.where(predicted_classes != j)[0].shape[0]
        
        error_rate = error_count / 10000.
        print 'Error rate for M={0} is {1}'.format(M, error_rate)
