import numpy as np

m1 = np.array([[0],[0]])
s1 = np.array([[1,0],[0,0.1]])

m2 = np.array([[0],[2]])
s2 = np.array([[0.1,0],[0,1]])

def estimate_from_training_sample(n_samples=5):
    # Generate the first sample
    # Since the covariances are diagonal, the componentwise sqrt is enough.
    sample1 = np.random.randn(2, n_samples)
    sample1 = np.dot(np.sqrt(s1), sample1)
    
    # Generate the second sample.
    sample2 = np.random.randn(2, n_samples)
    sample2 = np.dot(np.sqrt(s2), sample2)
    sample2 = m2 + sample2

    # Calculate estimated means by averaging along axis 1
    est_mean1 = np.reshape(sample1.mean(1), (2,1))
    est_mean2 = np.reshape(sample2.mean(1), (2,1))

    est_cov1 = np.dot(sample1 - est_mean1, (sample1 - est_mean1).T) / n_samples
    est_cov2 = np.dot(sample2 - est_mean2, (sample2 - est_mean2).T) / n_samples

    return est_mean1, est_cov1, est_mean2, est_cov2

'''
Calculates the decision boundary between two distributions specified
in the arguments. Returns A, b, c where the boundary is
x^TAx+b^Tx+c=0
'''
def calculate_quad_boundary(mean1, cov1, mean2, cov2):
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
    b = mean2.T * prec2 - mean1.T * prec1

    # Finally, the quadratic matrix term is the difference in the precision matrices
    A = 0.5 * (prec1 - prec2)
    return A, b, c

'''

