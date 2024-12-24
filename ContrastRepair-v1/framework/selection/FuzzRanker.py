from loguru import logger

from framework.selection.ExceptionRanker import ExceptionRanker
from framework.selection.AssertRanker import AssertRanker

class FuzzRanker:

    def __init__(self, pair_type: str, exception_file: str, assert_file: str=None,
                 pair_prob_fail: float = 0.5, pair_prob_succ: float = 0.5):
        self._pair_type = pair_type
        assert self._pair_type in ['no', 'exception', 'assert', 'both']

        if self._pair_type.lower() != 'no':
            self._exception_file = exception_file
            self._assert_file = assert_file

            self._exception_ranker = ExceptionRanker(exception_file, pair_prob_fail, pair_prob_succ)
            self._assert_ranker = AssertRanker(assert_file, pair_prob_fail, pair_prob_succ)

    def selection(self, pairs: int, top_k: int):

        if self._pair_type.lower() == 'no':
            select_pairs = []
        elif self._pair_type.lower() == 'both':
            exception_pairs = self._exception_ranker.selection(pairs, top_k)
            assert_pairs = self._assert_ranker.selection(pairs, top_k)
            select_pairs = [exception_pairs, assert_pairs]
        elif self._pair_type.lower() == 'exception':
            select_pairs = self._exception_ranker.selection(pairs, top_k)
            select_pairs = [select_pairs]
        elif self._pair_type.lower() == 'assert':
            select_pairs = self._assert_ranker.selection(pairs, top_k)
            select_pairs = [select_pairs]
        else:
            logger.error('Not support pair type: {}', self._pair_type)
            raise KeyError()

        return select_pairs


if __name__ == '__main__':
    import os
    ex_file_path = '/Users/Desktop/PhD/Conferences/2024-FSE/ChatFuzz/projects/ChatARP/data/Cases/Lang-48.json'
    as_file_path = '/Users/Desktop/PhD/Conferences/2024-FSE/ChatFuzz/projects/ChatARP/data/Cases/Lang-48_Assert.json'

    if not os.path.exists(ex_file_path):
        ex_file_path = None

    if not os.path.exists(as_file_path):
        as_file_path = None

    cc = FuzzRanker('assert', ex_file_path, as_file_path)

    for i in range(2000):
        a_succ = cc.selection(2, 1)
        logger.debug(a_succ)
        # for item in a_succ:
        #     for k, v in item.items():
        #         logger.debug('{}:{}', k, v)
        # a_succ = cc.selection(2, 1, False, False)
        # for item in a_succ:
        #     for k, v in item.items():
        #         logger.debug('{}:{}', k, v)
        # a_succ = cc.selection(2, 1, False, False)
        # for item in a_succ:
        #     for k, v in item.items():
        #         logger.debug('{}:{}', k, v)
    #
    # logger.info(a_succ)
    # logger.info(a_fail)
    #
    # a_succ, a_fail = cc.selection(4, False)
    #
    # logger.info(a_succ)
    # logger.info(a_fail)