"""Independent geometry and denominator checks for the benchmark."""
import unittest
import numpy as np
from starter.kitti_io import KittiCalib, KittiObject
from starter.projection import box3d_corners_cam
from src.exp_yaw_sweep import points_in_box, evaluate


class MetricTests(unittest.TestCase):
    def test_rotated_bottom_center_box(self):
        obj = KittiObject('Car', 0, 0, 0, np.zeros(4),
                          np.array([2, 2, 4]), np.array([3, 4, 10]), np.pi / 2)
        # Local long axis becomes camera z, and y above bottom center is inside.
        points = np.array([[3, 3, 11.9], [4.1, 3, 10], [3, 4.1, 10],
                           [3, 1.9, 10], [3, 3, 12.1]])
        np.testing.assert_array_equal(points_in_box(points, obj), [True, False, False, False, False])
        corners = box3d_corners_cam(obj)
        center = obj.location + [0, -1, 0]
        self.assertTrue(points_in_box(center + .999 * (corners - center), obj).all())

    def test_out_of_image_is_miss_and_absent_class_is_nan(self):
        calib = KittiCalib(np.eye(3, 4), np.eye(3), np.eye(3, 4))
        obj = KittiObject('Car', 0, 0, 0, np.array([0, 0, 2, 2]),
                          np.ones(3), np.array([0, 0, 1]), 0)
        points = np.array([[1, 1, 1, 0], [20, 1, 1, 0]])
        fr = dict(calib=calib, image=np.zeros((10, 10, 3), np.uint8))
        total, stats = evaluate(fr, points, [(obj, np.array([True, True]))], 0)
        self.assertEqual(total['object_points'], 2)
        self.assertEqual(total['inside_image'], 1)
        self.assertEqual(total['hits'], 1)
        self.assertEqual(total['hit_ratio'], .5)
        self.assertTrue(np.isnan(stats['Pedestrian']['hit_ratio']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
