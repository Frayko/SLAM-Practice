"""
Код для icp был взят отсюда: https://stackoverflow.com/questions/20120384/iterative-closest-point-icp-implementation-on-python
"""

import sys
import time
import cv2
import numpy
import scipy.optimize
import sklearn.neighbors


def icp(a, b, max_time=10):
    def res(p, src, dst):
        T = numpy.matrix(
            [[numpy.cos(p[2]), -numpy.sin(p[2]), p[0]],
             [numpy.sin(p[2]), numpy.cos(p[2]), p[1]],
             [0, 0, 1]]
        )
        n = numpy.size(src, 0)
        xt = numpy.ones([n, 3])
        xt[:, :-1] = src
        xt = (xt * T.T).A
        d = numpy.zeros(numpy.shape(src))
        d[:, 0] = xt[:, 0] - dst[:, 0]
        d[:, 1] = xt[:, 1] - dst[:, 1]
        r = numpy.sum(numpy.square(d[:, 0]) + numpy.square(d[:, 1]))
        return r

    def jac(p, src, dst):
        T = numpy.matrix(
            [[numpy.cos(p[2]), -numpy.sin(p[2]), p[0]],
             [numpy.sin(p[2]), numpy.cos(p[2]), p[1]],
             [0, 0, 1]]
        )
        n = numpy.size(src, 0)
        xt = numpy.ones([n, 3])
        xt[:, :-1] = src
        xt = (xt * T.T).A
        d = numpy.zeros(numpy.shape(src))
        d[:, 0] = xt[:, 0] - dst[:, 0]
        d[:, 1] = xt[:, 1] - dst[:, 1]
        dUdth_R = numpy.matrix(
            [[-numpy.sin(p[2]), -numpy.cos(p[2])],
             [numpy.cos(p[2]), -numpy.sin(p[2])]]
        )
        dUdth = (src * dUdth_R.T).A
        g = numpy.array(
            [numpy.sum(2 * d[:, 0]),
             numpy.sum(2 * d[:, 1]),
             numpy.sum(2 * (d[:, 0] * dUdth[:, 0] + d[:, 1] * dUdth[:, 1]))]
        )
        return g

    def hess(p, src, dst):
        n = numpy.size(src, 0)
        T = numpy.matrix(
            [[numpy.cos(p[2]), -numpy.sin(p[2]), p[0]],
             [numpy.sin(p[2]), numpy.cos(p[2]), p[1]],
             [0, 0, 1]]
        )
        n = numpy.size(src, 0)
        xt = numpy.ones([n, 3])
        xt[:, :-1] = src
        xt = (xt * T.T).A
        d = numpy.zeros(numpy.shape(src))
        d[:, 0] = xt[:, 0] - dst[:, 0]
        d[:, 1] = xt[:, 1] - dst[:, 1]
        dUdth_R = numpy.matrix([[-numpy.sin(p[2]), -numpy.cos(p[2])], [numpy.cos(p[2]), -numpy.sin(p[2])]])
        dUdth = (src * dUdth_R.T).A
        H = numpy.zeros([3, 3])
        H[0, 0] = n * 2
        H[0, 2] = numpy.sum(2 * dUdth[:, 0])
        H[1, 1] = n * 2
        H[1, 2] = numpy.sum(2 * dUdth[:, 1])
        H[2, 0] = H[0, 2]
        H[2, 1] = H[1, 2]
        d2Ud2th_R = numpy.matrix([[-numpy.cos(p[2]), numpy.sin(p[2])], [-numpy.sin(p[2]), -numpy.cos(p[2])]])
        d2Ud2th = (src * d2Ud2th_R.T).A
        H[2, 2] = numpy.sum(
            2 * (numpy.square(dUdth[:, 0]) + numpy.square(dUdth[:, 1]) + d[:, 0] * d2Ud2th[:, 0] + d[:, 0] * d2Ud2th[:,
                                                                                                             0])
        )
        return H

    t0 = time.time()
    init_pose = (0, 0, 0)
    src = numpy.array([a.T], copy=True).astype(numpy.float32)
    dst = numpy.array([b.T], copy=True).astype(numpy.float32)
    Tr = numpy.array(
        [[numpy.cos(init_pose[2]), -numpy.sin(init_pose[2]), init_pose[0]],
         [numpy.sin(init_pose[2]), numpy.cos(init_pose[2]), init_pose[1]],
         [0, 0, 1]]
    )
    # print("src", numpy.shape(src))
    # print("Tr[0:2]", numpy.shape(Tr[0:2]))
    src = cv2.transform(src, Tr[0:2])
    # src = transform_points_array(src, Tr)
    p_opt = numpy.array(init_pose)
    T_opt = numpy.array([])
    error_max = sys.maxsize
    first = False
    while not (first and time.time() - t0 > max_time):
        distances, indices = sklearn.neighbors.NearestNeighbors(n_neighbors=1, algorithm='auto', p=3).fit(
            dst[0]
        ).kneighbors(src[0])
        p = scipy.optimize.minimize(
            res, [0, 0, 0], args=(src[0], dst[0, indices.T][0]), method='Newton-CG', jac=jac, hess=hess
        ).x
        T = numpy.array([[numpy.cos(p[2]), -numpy.sin(p[2]), p[0]], [numpy.sin(p[2]), numpy.cos(p[2]), p[1]]])
        p_opt[:2] = (p_opt[:2] * numpy.matrix(T[:2, :2]).T).A
        p_opt[0] += p[0]
        p_opt[1] += p[1]
        p_opt[2] += p[2]
        src = cv2.transform(src, T)
        # src = transform_points_array(src, T)
        Tr = (numpy.matrix(numpy.vstack((T, [0, 0, 1]))) * numpy.matrix(Tr)).A
        error = res([0, 0, 0], src[0], dst[0, indices.T][0])

        if error < error_max:
            error_max = error
            first = True
            T_opt = Tr

    p_opt[2] = p_opt[2] % (2 * numpy.pi)
    return T_opt, error_max