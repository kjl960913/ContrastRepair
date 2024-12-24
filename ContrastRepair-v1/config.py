from typing import List
from dataclasses import dataclass


@dataclass
class Config:
    specific_bug: List

    openai_key: str = ''
    result_folder: str = '/workspace/experiments/ContrastR'

    # dataset
    dataset: str = 'defects4j-1.2-function' # ["defects4j-1.2-function", "defects4j-1.2-single-hunk", "defects4j-1.2-single-line"]
    dataset_folder: str = '/workspace/ContrastAPR/data/Defects4j'
    if dataset == 'quixbugs-java':
        case_folder: str = '/root/QuixBugs/json4java'
    elif dataset == 'quixbugs-python':
        case_folder: str = '/root/QuixBugs/json4python'
    else:
        case_folder: str = '/workspace/ContrastAPR/data/Cases'
    # single_hunk:bool = False
    # single_line:bool = False

    # framework
    # pre-process
    java_tool: str = '/workspace/ContrastAPR/jp.jar'
    # iteration
    repair_mode: str = 'repair'  # ['repair', 'patch_augment']
    repair_tool: str = 'function'  # ['function', 'single-hunk', 'single-line']
    total_tries: int = 40
    repeat_num: int = 3
    repeat_mode: str = 'iterative'  # ['same', 'iterative']
    pair_type: str = 'both'  # ['no', 'exception', 'assert', 'both']
    pair_prob_fail: float = 0.5
    pair_prob_succ: float = 0.5
    bug_type: str = 'all'  # 'all' for all
    skip_val: bool = False
    chatgpt_parser: str = 'simple'  # 'simple' for single-function, 'complex' for single-line and hunk
    temperature: float = 1.0

    # validation
    tmp_prefix: str = 'test'

    # similarity
    # corpus_update_frequency: int = 10
    pairs: int = 2
    top_k: int = 1
    weight: float = 0.5

    __instance = None

    def __init__(self) -> None:
        self._set_others()
        Config.__instance = self

    def _set_others(self):
        self.specific_bug = []  # ['Lang-1', 'Lang-5'] # [] for all
        # self.specific_bug = ['Time-20']

    @staticmethod
    def get_instance() -> 'Config':
        """
        Gets the singleton instance

        :returns: instance
        :rtype: ViolationTracker
        """
        return Config.__instance


if __name__ == '__main__':
    a = Config()
    print(a.get_instance().specific_bug)
