import numpy as np
import matplotlib.pyplot as plt

m1 = np.array([[0],[0]])
s1 = np.array([[1,0],[0,0.1]])

m2 = np.array([[0],[2]])
s2 = np.array([[0.1,0],[0,1]])

def get_samples(n_samples=5):
    # Generate the first sample
    # Since the covariances are diagonal, the componentwise sqrt is enough.
    sample1 = np.random.randn(2, n_samples)
    sample1 = np.dot(np.sqrt(s1), sample1)
    
    # Generate the second sample.
    sample2 = np.random.randn(2, n_samples)
    sample2 = np.dot(np.sqrt(s2), sample2)
    sample2 = m2 + sample2

    return sample1, sample2

def get_nonpooled_estimate(sample1, sample2):
    n_samples = sample1.shape[1]

    # Calculate estimated means by averaging along axis 1
    est_mean1 = np.reshape(sample1.mean(1), (2,1))
    est_mean2 = np.reshape(sample2.mean(1), (2,1))

    est_cov1 = np.dot(sample1 - est_mean1, (sample1 - est_mean1).T) / n_samples
    est_cov2 = np.dot(sample2 - est_mean2, (sample2 - est_mean2).T) / n_samples

    return est_mean1, est_cov1, est_mean2, est_cov2

def get_pooled_estimate(sample1, sample2):
    n_samples = sample1.shape[1]

    est_mean1 = np.reshape(sample1.mean(1), (2,1))
    est_mean2 = np.reshape(sample2.mean(1), (2,1))

    est_cov1 = np.dot(sample1 - est_mean1, (sample1 - est_mean1).T) / n_samples
    est_cov2 = np.dot(sample2 - est_mean2, (sample2 - est_mean2).T) / n_samples
    # Since the number of samples from each class is the same, the pooled covariance is just
    # the average of the two.
    est_cov = 0.5 * (est_cov1 + est_cov2)

    return est_mean1, est_mean2, est_cov

'''
Calculates the decision boundary between two distributions specified
in the arguments. Returns A, b, c where the boundary is
x^TAx+b^Tx+c=0
'''
def calculate_boundary(mean1, cov1, mean2, cov2):
    # Convert everything into matrices so we can do the multiplications concisely
    mean1 = np.matrix(mean1)
    cov1 = np.matrix(cov1)
    mean2 = np.matrix(mean2)
    cov2 = np.matrix(cov2)

    # Logs of the determinants
    logdet1 = np.log(np.linalg.det(cov1))
    logdet2 = np.log(np.linalg.det(cov2))

    # Precision matrices
    prec1 = np.linalg.inv(cov1)
    prec2 = np.linalg.inv(cov2)

    # Calculate the constant term
    c = logdet1 - logdet2 + 0.5*(mean1.T * prec1 * mean1) - 0.5*(mean2.T * prec2 * mean2)

    # Calculate the linear term
    b = (mean2.T * prec2 - mean1.T * prec1).T

    # Finally, the quadratic matrix term is the difference in the precision matrices
    A = 0.5 * (prec1 - prec2)
    return A, b, c

'''
Returns a tuple (X,Y,Z) of arguments suitable to passing into the contour plot command
Takes A, b, c as parameters (of the quadratic)
'''
def get_contour_params(A, b, c):
    A = A.A
    b = b.T.A[0]
    c = c.A[0,0]

    xc = np.linspace(-2, 2, 100)
    yc = np.linspace(-2, 5, 100)

    X, Y = np.meshgrid(xc, yc)
    Z = A[0,0] * X**2 + A[1,1] * Y**2 + (A[0,1] + A[1,0])*X*Y
    Z += b[0]*X + b[1]*Y
    Z += c
    return X,Y,Z

'''
Calculates the error rate for classifying the test-samples d1_test and d2_test
Classification criterion is that x^TAx+b^Tx+c < 0 for class 1 and otherwise
class 2. Returns a float that's the error rate
'''
def get_error_rate(params, d1_test, d2_test):
    A, b, c = params
    d1_test = np.asmatrix(d1_test)
    d2_test = np.asmatrix(d2_test)

    d1_eval = np.empty(d1_test.shape[1])
    d2_eval = np.empty(d2_test.shape[1])
    
    for i in range(d1_test.shape[1]):
        d1_pt = d1_test[:, i]
        d2_pt = d2_test[:, i]
        d1_eval[i] = (d1_pt.T * A * d1_pt + b.T * d1_pt + c).A[0,0]
        d2_eval[i] = (d2_pt.T * A * d2_pt + b.T * d2_pt + c).A[0,0]
    
    err_rate = (np.where(d1_eval >= 0)[0].shape[0] + np.where(d2_eval < 0)[0].shape[0]) / float(2 * d1_test.shape[1])

    return err_rate


'''
Runs the top-level commands
'''
def p7():
    samples = get_samples(5)
    nonpooled_est = get_nonpooled_estimate(*samples)
    pooled_est = get_pooled_estimate(*samples)

    true_bnd = calculate_boundary(m1, s1, m2, s2)
    nonpooled_bnd = calculate_boundary(*nonpooled_est)
    pooled_bnd = calculate_boundary(pooled_est[0], pooled_est[2], pooled_est[1], pooled_est[2])

    true_contour = get_contour_params(*true_bnd)
    nonpooled_contour = get_contour_params(*nonpooled_bnd)
    pooled_contour = get_contour_params(*pooled_bnd)

    plt.figure()
    plt.contour(*true_contour, levels=([0]), colors='k')
    plt.contour(*nonpooled_contour, levels=([0]), colors='r')
    plt.contour(*pooled_contour, levels=([0]), colors='b')

    d1_test, d2_test = get_samples(1000)
    true_error = get_error_rate(true_bnd, d1_test, d2_test)
    pooled_error = get_error_rate(pooled_bnd, d1_test, d2_test)
    nonpooled_error = get_error_rate(nonpooled_bnd, d1_test, d2_test)
    print true_error, pooled_error, nonpooled_error
