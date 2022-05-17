from abc import abstractmethod
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import numpy as np

import cv2

from . import oakd_source
from . import visualizer
from . import methods
from .cre_stereo import CREStereo

def parse_args():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--oak', action='store_true', help='Use an oak-D camera to grab images.')
    parser.add_argument('--images',
                        help='left_image1 ... [left_imageN] right_image1 ... [right_imageN]. Load image pairs from disk. Provide all the left images first, then all the right images, both rectified.',
                        type=Path, 
                        default=None,
                        nargs='+')
    parser.add_argument('--calibration', type=Path, help='Calibration json. If unspecified, it will try to load a stereodemo_calibration.json file in the left image parent folder.', default=None)
    return parser.parse_args()

class FileListSource (visualizer.Source):
    def __init__(self, file_list, calibration=None):
        assert len(file_list) % 2 == 0
        N = len(file_list) // 2
        self.left_images_path = file_list[:N]
        self.right_images_path = file_list[N:]
        self.index = 0
        self.user_provided_calibration_path = calibration

    def get_next_pair(self):
        if self.index >= len(self.left_images_path):
            self.index = 0

        def load_image(path):
            return cv2.imread(str(path), cv2.IMREAD_COLOR)

        left_image_path = self.left_images_path[self.index]
        left_image = load_image(left_image_path)
        if self.user_provided_calibration_path is None:
            calibration_path = left_image_path.parent / 'stereodemo_calibration.json'
            if not calibration_path.exists():
                print (f"Warning: no calibration file found {calibration_path}. Using default calibration, the point cloud won't be accurate.")
                calibration_path = None
        else:
            calibration_path = self.user_provided_calibration_path
        if calibration_path:
            calib = visualizer.Calibration.from_json (open(calibration_path, 'r').read())
        else:
            # Fake reasonable calibration.
            calib = visualizer.Calibration(left_image.shape[1],
                                           left_image.shape[0],
                                           left_image.shape[0]*0.8,
                                           left_image.shape[0]*0.8,
                                           left_image.shape[1]/2.0,
                                           left_image.shape[0]/2.0,
                                           0.075)
            
        right_image_path = self.right_images_path[self.index]
        self.index += 1
        status = f"{left_image_path} / {right_image_path}"
        return visualizer.InputPair (load_image(left_image_path), load_image(right_image_path), calib, status)

def main():
    method_list = [
        methods.StereoBMMethod(),
        methods.StereoSGBMMethod(),
        CREStereo()
    ]

    args = parse_args()

    if args.images is not None:
        source = FileListSource(args.images, args.calibration)
    elif args.oak:
        from .oakd_source import OakdSource, StereoFromOakInputSource
        source = OakdSource()
        method_list = [StereoFromOakInputSource()] + method_list
    else:
        print ("You need to specify --oak or --images")
        sys.exit (1)

    method_dict = { method.name:method for method in method_list } 

    viz = visualizer.Visualizer(method_dict, source)

    while True:
        start_time = time.time()
        if not viz.update_once ():
            break
        cv2.waitKey (1)
        elapsed = time.time() - start_time
        time_to_sleep = 1/30.0 - elapsed
        if time_to_sleep > 0:
            time.sleep (time_to_sleep)


