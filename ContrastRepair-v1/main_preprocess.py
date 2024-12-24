import os
import sys
import json
import openai

from dataclasses import asdict
from loguru import logger

from config import Config
from framework.data.DataLoader import Defects4j12
from framework.repair.ContrastRepairFunction import ContrastRepairFunction
# from framework.repair.ContrastRepairSingleHunk import ContrastRepairSingleHunk
# from framework.repair.ContrastRepairSingleLine import ContrastRepairSingleLine
from framework.runner.BuggyProcesser import BuggyProcessor
java_home_path = "/root/jdk1.8.0_371"
os.environ["JAVA_HOME"] = java_home_path
level = "DEBUG"
logger.configure(handlers=[{"sink": sys.stderr, "level": level}]) # TODO: fix file output

def repair(bugs):
    sys_config = Config.get_instance()
    openai.api_key = sys_config.openai_key
    repair_tool = sys_config.repair_tool
    assert repair_tool in ['function', 'single-hunk', 'single-line']
    if repair_tool == 'function':
        contrast_repair = ContrastRepairFunction(sys_config.total_tries, sys_config.repeat_num, sys_config.repeat_mode, sys_config.pair_type, sys_config.chatgpt_parser)
    else:
        logger.error('Not support chat repair: {}', repair_tool)
        raise KeyError()

    logger.info('====> Start repair')
    contrast_repair.repair(bugs)

def preprocess(bugs, initial_stage=True):
    sys_config = Config.get_instance()
    buggy_pro = BuggyProcessor(sys_config.result_folder, sys_config.java_tool)

    for bug_id, bug_func_info in bugs.items():
        if initial_stage:
            # if os.path.exists('/workspace/experiments/ContrastR/'+bug_id):
            #     continue
            buggy_pro.initial_stage(bug_id, bug_func_info['func_name'],
                                    bug_func_info['start_line'], bug_func_info['end_line'])
        buggy_pro.mutation_stage(bug_id)
        buggy_pro.verification_stage(bug_id)

def main():
    # step 1: create config file & logger file
    sys_config = Config()

    if not os.path.exists(sys_config.result_folder):
        os.makedirs(sys_config.result_folder)
    else:
        logger.warning('Result folder exists: {}. Might overwrite previous results.', sys_config.result_folder)

    config_file = os.path.join(sys_config.result_folder, 'config.json')
    with open(config_file, 'w') as f:
        json.dump(asdict(sys_config), f, indent=4)

    log_file = os.path.join(sys_config.result_folder, 'system.log')
    if os.path.exists(log_file):
        os.remove(log_file)
    logger.add(log_file, level=level)

    # load dataset
    if sys_config.dataset == "defects4j-1.2-function":
        bugs, bugs_func_info = Defects4j12.get_data(sys_config.dataset_folder, sub_type=sys_config.bug_type, specific_type=sys_config.specific_bug)
    elif sys_config.dataset == "defects4j-1.2-single-hunk":
        bugs, bugs_func_info = Defects4j12.get_data(sys_config.dataset_folder, sub_type=sys_config.bug_type, specific_type=sys_config.specific_bug, single_hunk=True)
    elif sys_config.dataset == "defects4j-1.2-single-line":
        bugs, bugs_func_info = Defects4j12.get_data(sys_config.dataset_folder, sub_type=sys_config.bug_type, specific_type=sys_config.specific_bug, single_line=True)
    else:
        logger.error('Not support dataset {}', sys_config.dataset)
        raise KeyError()

    # preprocess
    preprocess(bugs_func_info)

if __name__ == '__main__':
    main()
