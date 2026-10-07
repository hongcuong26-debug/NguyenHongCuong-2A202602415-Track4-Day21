"""Run geometry checks with: python -m src.test_projection."""
import unittest
import warnings

import numpy as np

from starter.kitti_io import KittiCalib, load_calib
from starter.projection import cam_to_image, velo_to_cam


class ProjectionTests(unittest.TestCase):
    def test_translation_and_input(self):
        transform = np.column_stack((np.eye(3), [1, 2, 3]))
        calib = KittiCalib(np.eye(3, 4), np.eye(3), transform)
        points = np.array([[4., 5., 6.]])
        original = points.copy()
        np.testing.assert_allclose(velo_to_cam(points, calib), [[5, 7, 9]])
        np.testing.assert_array_equal(points, original)
        self.assertEqual(velo_to_cam(np.empty((0, 3)), calib).shape, (0, 3))
        with self.assertRaises(ValueError):
            velo_to_cam(np.zeros((2, 4)), calib)

    def test_filtering_order_and_boundaries(self):
        points = np.array([[2, 4, 2], [1, 1, -1], [1, 1, 0],
                           [np.nan, 0, 1], [0, np.inf, 1], [10, 1, 1],
                           [1, 10, 1], [-1, 0, 1], [0, 0, 1], [6, 3, 3],
                           [0, 0, .1]])
        with warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            uv, depth, mask = cam_to_image(points, np.eye(3, 4), (10, 10))
        expected = np.zeros(len(points), dtype=bool)
        expected[[0, 8, 9]] = True
        np.testing.assert_array_equal(mask, expected)
        np.testing.assert_allclose(uv, [[1, 2], [0, 0], [2, 1]])
        np.testing.assert_allclose(depth, points[mask, 2])

    def test_empty_and_zero_projective_scale(self):
        uv, depth, mask = cam_to_image(np.empty((0, 3)), np.eye(3, 4), (10, 10))
        self.assertEqual(uv.shape, (0, 2))
        self.assertEqual(depth.shape, (0,))
        self.assertEqual(mask.shape, (0,))
        with warnings.catch_warnings():
            warnings.simplefilter('error', RuntimeWarning)
            _, _, mask = cam_to_image(np.array([[1, 1, 2]]), np.zeros((3, 4)), (10, 10))
        self.assertFalse(mask.any())

    def test_synthetic_reference(self):
        calib = load_calib('data/synthetic/training/calib/000000.txt')
        cam = velo_to_cam(np.array([[10., 0., 0.]]), calib)
        uv, depth, mask = cam_to_image(cam, calib.P2, (375, 1242))
        self.assertAlmostEqual(cam[0, 2], 9.73, delta=.03)
        np.testing.assert_allclose(uv[0], [614, 175], atol=2)
        self.assertTrue(mask[0])
        print(f'Reference (10,0,0): camera={cam[0]}, pixel={uv[0]}')


if __name__ == '__main__':
    unittest.main(verbosity=2)
