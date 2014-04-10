from scipy.stats import norm
import matplotlib.pyplot as plt
import numpy as np


def compute_error_rates():
    error_rates = np.zeros(100)
    for i in range(100):
        sample1 = np.random.randn(10)
        sample2 = np.random.randn(10) + 2
        m1 = sample1.mean()
        m2 = sample2.mean()
        x = (m2*m2 - m1*m1)/(2*(m2-m1))
        error_rates[i] = 0.5*norm.cdf(x-m2)+0.5-0.5*norm.cdf(x-m1)

    
    plt.figure()
    hist, bins = np.histogram(error_rates, bins=50)
    width = 0.6*(bins[1] - bins[0])
    centers = (bins[:-1] + bins[1:]) / 2
    plt.bar(centers, hist, align='center', width=width)
    plt.savefig('p3.png', bbox_inches='tight')

    return error_rates
