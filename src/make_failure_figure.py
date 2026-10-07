"""Create annotated side-by-side pedestrian calibration drift evidence."""
import argparse
from pathlib import Path

import cv2
import numpy as np

from starter.projection import project_velo_to_image, perturb_extrinsic
from src.exp_yaw_sweep import prepare_frame, evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', default='data/kitti_mini', help='KITTI root')
    parser.add_argument('--frame', default='000011', help='Pedestrian frame')
    parser.add_argument('--yaw-deg', type=float, default=2, help='Failure yaw (degrees)')
    parser.add_argument('--out', default='results/figures/fail_01_yaw_2deg_pedestrian.png', help='Output PNG')
    args = parser.parse_args()
    fr, points, members = prepare_frame(args.data_root, args.frame)
    pedestrians = [(obj, membership) for obj, membership in members
                   if obj.type == 'Pedestrian' and membership.any()]
    if not pedestrians:
        raise ValueError('No pedestrian with LiDAR points in this frame')
    # Select a populated pedestrian whose measured hit loss is largest.
    candidates = []
    for obj, membership in pedestrians:
        base, _ = evaluate(fr, points, [(obj, membership)], 0)
        fail, _ = evaluate(fr, points, [(obj, membership)], args.yaw_deg)
        candidates.append((base['hit_ratio'] - fail['hit_ratio'], obj, membership))
    _, focus, membership = max(candidates, key=lambda item: item[0])
    print(f'Highlighted pedestrian bbox={focus.bbox.tolist()}, width={focus.bbox[2]-focus.bbox[0]:.2f}px, z={focus.location[2]:.2f}m')
    x1, y1, x2, y2 = focus.bbox
    height, width = fr['image'].shape[:2]
    left, right = max(0, int(x1)-75), min(width, int(x2)+75)
    top, bottom = max(0, int(y1)-45), min(height, int(y2)+35)
    panels, projected_focus = [], []
    for yaw in (0, args.yaw_deg):
        image = fr['image'].copy()
        uv, _, mask = project_velo_to_image(points, perturb_extrinsic(fr['calib'], yaw_deg=yaw), image.shape)
        focus_uv = uv[membership[mask]]
        projected_focus.append(focus_uv)
        for u, v in focus_uv:
            hit = x1 <= u <= x2 and y1 <= v <= y2
            cv2.circle(image, (int(u), int(v)), 2, (0, 255, 0) if hit else (0, 0, 255), -1)
        cv2.rectangle(image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 255), 2)
        crop = image[top:bottom, left:right]
        scale = min(600 / crop.shape[1], 600 / crop.shape[0])
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
        panel = np.zeros((700, 600, 3), dtype=np.uint8)
        offset_x = (600 - crop.shape[1]) // 2
        offset_y = 100 + (600 - crop.shape[0]) // 2
        panel[offset_y:offset_y+crop.shape[0], offset_x:offset_x+crop.shape[1]] = crop
        total, stats = evaluate(fr, points, members, yaw)
        cv2.putText(panel, f'Yaw {yaw:g} deg | Frame {args.frame}', (15, 30), cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
        cv2.putText(panel, f'Pedestrian hit ratio: {stats["Pedestrian"]["hit_ratio"]:.1%}', (15, 60), cv2.FONT_HERSHEY_SIMPLEX, .6, (255, 255, 255), 1)
        cv2.putText(panel, 'Yellow: GT box; green: hit; red: miss', (15, 85), cv2.FONT_HERSHEY_SIMPLEX, .55, (255, 255, 255), 1)
        panels.append(panel)
        print(f'yaw={yaw:g}: frame={total}, pedestrian={stats["Pedestrian"]}')
    if projected_focus[0].shape == projected_focus[1].shape:
        shift = np.median(projected_focus[1] - projected_focus[0], axis=0)
        print(f'Median highlighted-point shift (u,v): {shift.tolist()} px')
    print(f'f*tan(yaw)={fr["calib"].P2[0,0] * np.tan(np.deg2rad(args.yaw_deg)):.4f} px')
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(out), np.hstack(panels)):
        raise OSError(f'Cannot write {out}')


if __name__ == '__main__':
    main()
