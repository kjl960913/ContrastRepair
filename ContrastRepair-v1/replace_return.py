import openai
import glob
import os
import sys

from loguru import logger
from framework.filters.ParameterFilter import ParameterFilter
from config import Config

level = "DEBUG"
logger.configure(handlers=[{"sink": sys.stderr, "level": level}]) # TODO: fix file output

cfg = Config()
openai.api_key = cfg.openai_key

if not os.path.exists(cfg.result_folder):
    os.makedirs(cfg.result_folder)

log_file = os.path.join(cfg.result_folder, 'ParameterFilter.log')
if os.path.exists(log_file):
    os.remove(log_file)
logger.add(log_file, level=level)

pf = ParameterFilter()

buggy_folder = '/Users/Desktop/PhD/Conferences/2024-FSE/ChatFuzz/projects/ChatARP/data/PreProcess/buggyfunctions'

for file_path in glob.glob(os.path.join(buggy_folder, '*.txt')):
    idx = os.path.basename(file_path).split('.')[0]
    with open(file_path, 'r') as f:
        source_code = f.readlines()
    source_code = ''.join(source_code)
    pf.query(idx, source_code)
    break
    # break