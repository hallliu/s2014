import numpy as np
import scipy.linalg as sp
import matplotlib.pyplot as plt

def run_gibbs_normal(n_samp, epsilon):
    r1 = np.array([2+epsilon, -1, 0, -1])
    prec = sp.circulant(r1)
    samples = np.zeros((4, n_samp), dtype='float64')
    running_sample = np.zeros(4, dtype='float64')

    # Precompute 40k std normal samples
    std_normal_samples = np.random.randn(4*n_samp)
    
    # Run 10000 iterations over all 4 coordinates
    for i in range(n_samp):
        for j in range(4):
            mean = np.dot(prec[j], running_sample) - prec[j, j]*running_sample[j]
            mean /= -prec[j, j]
            std = np.sqrt(1/prec[j, j])
            running_sample[j] = std_normal_samples[i*4+j] * std + mean
        samples[:, i] = running_sample

    return samples

def plot_trajectories(samples):
    plt.figure(figsize=(14,10))
    plt.subplot(221)
    plt.plot(samples[0])
    plt.subplot(222)
    plt.plot(samples[1])
    plt.subplot(223)
    plt.plot(samples[2])
    plt.subplot(224)
    plt.plot(samples[3])

def est_covs(samples, epsilon):
    c1 = samples[:,:1000]
    cf = samples[:,-1000:]
    
    r1 = np.array([2+epsilon, -1, 0, -1])
    Q = sp.circulant(r1)

    return 4-np.trace(np.dot(Q,np.cov(c1))), 4-np.trace(np.dot(Q, np.cov(cf))), 4-np.trace(np.dot(Q,np.cov(samples)))


def make_gibbs_hist(epsilon):
    total_rhos = np.zeros(100)

    r1 = np.array([2+epsilon, -1, 0, -1])
    Q = sp.circulant(r1)
    for i in range(100):
        sample = run_gibbs_normal(10000, epsilon)
        total_rhos[i] = 4-np.trace(np.dot(Q, np.cov(sample)))
    plt.hist(total_rhos)

def make_direct_hist(epsilon):
    total_rhos = np.zeros(100)

    r1 = np.array([2+epsilon, -1, 0, -1])
    Q = sp.circulant(r1)
    tm = sp.inv(sp.cholesky(Q))
    for i in range(100):
        std_sample = np.random.randn(4,10000)
        sample = np.dot(tm, std_sample)
        total_rhos[i] = 4 - np.trace(np.dot(Q, np.cov(sample)))
    plt.hist(total_rhos)

def run_gibbs_binary(n_samp):
    samples = np.zeros((4, n_samp), dtype='int')
    running_sample = np.ones(4, dtype='int')

    # Precompute uniform samples
    std_unif_samples = np.random.rand(4*n_samp)
    
    # Run 10000 iterations over all 4 coordinates
    for i in range(n_samp):
        for j in range(4):
            if running_sample[j] == 1:
                pos_comp = running_sample
                neg_comp = running_sample.copy()
                neg_comp[j] = -1
            if running_sample[j] == -1:
                neg_comp = running_sample
                pos_comp = running_sample.copy()
                pos_comp[j] = 1
            pos_exp = np.exp(np.dot(pos_comp, np.roll(pos_comp, 1)))
            neg_exp = np.exp(np.dot(neg_comp, np.roll(neg_comp, 1)))
            pos_prob = pos_exp / (pos_exp + neg_exp)
            if std_unif_samples[i*4+j] < pos_prob:
                running_sample[j] = 1
            else:
                running_sample[j] = -1

        samples[:, i] = running_sample
    return samples

def compute_bin_probs():
    import itertools
    probs = []
    states = []
    for c in itertools.product([-1,1], repeat=4):
        k = np.array(c)
        probs.append(np.exp(np.dot(k, np.roll(k, 1))))
        statestr = []
        for i in range(4):
            statestr.append(str((c[i]+1)/2))
        states.append(''.join(statestr))
    probs = np.array(probs)
    probs /= probs.sum()

    
    return probs, states

def make_binary_traj_plot(sample):
    sample_len = sample.shape[1]
    import itertools
    actual_probs = compute_bin_probs()[0]
    state_to_ind = {}
    for k, c in enumerate(itertools.product([-1,1], repeat=4)):
        statestr = []
        for i in range(4):
            statestr.append(str((c[i]+1)/2))
        state_to_ind[''.join(statestr)] = k

    counts = np.zeros((16, sample_len))
    running_count = np.zeros(16)
    for k in range(sample.shape[1]):
        statestr = []
        for i in range(4):
            statestr.append(str((sample[i, k]+1)/2))
        running_count[state_to_ind[''.join(statestr)]] += 1
        counts[:,k] = running_count

    freqs = counts.astype('float64') / np.arange(1, sample_len+1) 
    traj = freqs / actual_probs[:, np.newaxis]

    for i in range(16):
        plt.plot(np.arange(1, sample_len+1), traj[i])
    plt.ylim((0, 5))
