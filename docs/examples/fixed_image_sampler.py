#!/usr/bin/python3
#
# Load images/all_shapes.png and images/shape_blue_circle.png
# as a part of haystack and needle, then find the needle in
# the haystack, and dump the results of the matching in a
# tmp folder in examples. The main purpose of this sample is
# to be reused as a tool for matching fixed needle/haystack
# pairs in order to figure out the best parameter configuration
# for successful matching.

import os
import sys

import logging
import shutil
import argparse

# only needed if not installed system wide
this_path = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(this_path, '../..')))

from guibot.config import GlobalConfig
from guibot.imagelogger import ImageLogger
from guibot.fileresolver import FileResolver
from guibot.errors import *
from guibot.target import *
from guibot.finder import *


# argument parsing setup
parser = argparse.ArgumentParser(description='Fixed Image Sampler')
parser.add_argument('--backend', type=str, default="none", help='Finder backend used to determine the target type')
parser.add_argument('--needle', type=str, default='shape_blue_circle', help='Needle image filename')
parser.add_argument('--haystack', type=str, default='all_shapes', help='Haystack image filename')
parser.add_argument('--match', type=str, default='', help='Match file to use for finding')
parser.add_argument('--logpath', type=str, default='./tmp/', help='Path for image logging')
parser.add_argument('--remove_logpath', action='store_true', help='Remove logpath after execution')
args = parser.parse_args()

# parameters to toy with
file_resolver = FileResolver()
file_resolver.add_path(os.path.join(this_path, "images"))
BACKEND = args.backend
# could be Text('Text') or any other target type
if BACKEND == "text":
    NEEDLE = Text(args.needle)
elif BACKEND in ["cascade", "deep"]:
    NEEDLE = Pattern(args.needle)
else:
    NEEDLE = Image(args.needle)
HAYSTACK = Image(args.haystack)
# image logging variables
LOGPATH = args.logpath
REMOVE_LOGPATH = args.remove_logpath

# overall logging setup
handler = logging.StreamHandler()
logging.getLogger('').addHandler(handler)
logging.getLogger('').setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
GlobalConfig.image_logging_level = 0
GlobalConfig.image_logging_destination = LOGPATH
GlobalConfig.image_logging_step_width = 4
ImageLogger.step = 1

# Main configuration steps
GlobalConfig.find_backend = BACKEND
# example configuration from various finder types
if GlobalConfig.find_backend == "autopy":
    finder = AutoPyFinder(synchronize=False)
elif GlobalConfig.find_backend == "contour":
    finder = ContourFinder(synchronize=False)
elif GlobalConfig.find_backend == "template":
    finder = TemplateFinder(synchronize=False)
    #finder.configure_backend(backend="sqdiff_normed", category="template")
elif GlobalConfig.find_backend == "feature":
    finder = FeatureFinder(synchronize=False)
    #finder.params["feature"]["ransacReprojThreshold"].value = 25.0
    #finder.params["fdetect"]["MaxFeatures"].value = 10
elif GlobalConfig.find_backend == "cascade":
    finder = CascadeFinder(synchronize=False)
elif GlobalConfig.find_backend == "text":
    finder = TextFinder(synchronize=False)
    #finder.configure(text_detector="contours")
    #finder.params["text"]["datapath"].value = "../../misc"
    #finder.params["ocr"]["oem"].value = 0
    #finder.params["tdetect"]["verticalVariance"].value = 5
    #finder.params["threshold"]["blockSize"].value = 3
elif GlobalConfig.find_backend == "tempfeat":
    finder = TemplateFeatureFinder(synchronize=False)
    #finder.params["tempfeat"]["front_similarity"].value = 0.5
elif GlobalConfig.find_backend == "deep":
    finder = DeepFinder(synchronize=False)
else:
    raise TypeError(f"Unknown backend: {BACKEND}")
#finder.params["find"]["similarity"].value = 0.7

if args.match:
    finder = Finder.from_match_file(args.match)

# synchronize at this stage to take into account all configuration
finder.synchronize()

# Main matching step
finder.find(NEEDLE, HAYSTACK)


# Final cleanup steps
if REMOVE_LOGPATH:
    shutil.rmtree(LOGPATH)
GlobalConfig.image_logging_level = logging.ERROR
GlobalConfig.image_logging_destination = "./imglog"
GlobalConfig.image_logging_step_width = 3
