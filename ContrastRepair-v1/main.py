import os
import sys
import json
import openai

from dataclasses import asdict
from loguru import logger

from config import Config
from framework.data.DataLoader import Defects4j12, QuixBugs
from framework.repair.ContrastRepairFunction import ContrastRepairFunction
from framework.repair.ContrastRepairSingleHunk import ContrastRepairSingleHunk
from framework.repair.ContrastRepairSingleLine import ContrastRepairSingleLine

level = "DEBUG"
logger.configure(handlers=[{"sink": sys.stderr, "level": level}]) # TODO: fix file output


def repair(bugs):
    sys_config = Config.get_instance()
    openai.api_key = sys_config.openai_key
    repair_tool = sys_config.repair_tool
    assert repair_tool in ['function', 'single-hunk', 'single-line']
    if repair_tool == 'function':
        contrast_repair = ContrastRepairFunction(sys_config.total_tries, sys_config.repeat_num, sys_config.repeat_mode, sys_config.pair_type, sys_config.chatgpt_parser)
    elif repair_tool == 'single-hunk':
        contrast_repair = ContrastRepairSingleHunk(sys_config.total_tries, sys_config.repeat_num, sys_config.repeat_mode, sys_config.pair_type, sys_config.chatgpt_parser) # @todo: add
    elif repair_tool == 'single-line':
        contrast_repair = ContrastRepairSingleLine(sys_config.total_tries, sys_config.repeat_num, sys_config.repeat_mode, sys_config.pair_type, sys_config.chatgpt_parser)
    else:
        logger.error('Not support repair: {}', repair_tool)
        raise KeyError()

    logger.info('====> Start repair')
    contrast_repair.repair(bugs)


def plausible2correct(bugs):
    sys_config = Config.get_instance()
    openai.api_key = sys_config.openai_key
    repair_tool = sys_config.repair_tool
    assert repair_tool in ['function', 'single-hunk', 'single-line']
    if repair_tool == 'function':
        contrast_repair = ContrastRepairFunction(sys_config.total_tries, sys_config.repeat_num, sys_config.repeat_mode, sys_config.pair_type, sys_config.chatgpt_parser)
    elif repair_tool == 'single-hunk':
        contrast_repair = ContrastRepairSingleHunk(sys_config.total_tries, sys_config.repeat_num, sys_config.repeat_mode, sys_config.pair_type, sys_config.chatgpt_parser) # @todo: add
    elif repair_tool == 'single-line':
        contrast_repair = ContrastRepairSingleLine(sys_config.total_tries, sys_config.repeat_num, sys_config.repeat_mode, sys_config.pair_type, sys_config.chatgpt_parser)
    else:
        logger.error('Not support repair: {}', repair_tool)
        raise KeyError()

    logger.info('====> Start repair')
    contrast_repair.plausible_to_correct(bugs)

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

    log_file = os.path.join(sys_config.result_folder, 'system_interact_with_gpt.log')
    if os.path.exists(log_file):
        os.remove(log_file)
    logger.add(log_file, level=level)

    # load dataset
    if sys_config.dataset == "defects4j-1.2-function":
        bugs, bugAll = Defects4j12.get_data(sys_config.dataset_folder, sub_type=sys_config.bug_type, specific_type=sys_config.specific_bug)
    elif sys_config.dataset == "defects4j-1.2-single-hunk":
        bugs, bugAll = Defects4j12.get_data(sys_config.dataset_folder, sub_type=sys_config.bug_type, specific_type=sys_config.specific_bug, single_hunk=True)
    elif sys_config.dataset == "defects4j-1.2-single-line":
        bugs, bugAll = Defects4j12.get_data(sys_config.dataset_folder, sub_type=sys_config.bug_type, specific_type=sys_config.specific_bug, single_line=True)
    elif sys_config.dataset == "defects4j-2.0-single-line":
        bugs = Defects4j12.parse_defects4j_2(sys_config.dataset_folder)
    elif sys_config.dataset == "quixbugs-python":
        bugs = QuixBugs.parse_python()
    elif sys_config.dataset == "quixbugs-java":
        bugs = QuixBugs.parse_java()
    else:
        logger.error('Not support dataset {}', sys_config.dataset)
        raise KeyError()

    # start repair
    if sys_config.repair_mode == 'repair':
        repair(bugs)
    elif sys_config.repair_mode == 'patch_augment':
        plausible2correct(bugs)
    else:
        logger.error('Not support repair_mode {}', sys_config.repair_mode)
        raise KeyError()

if __name__ == '__main__':
    main()
