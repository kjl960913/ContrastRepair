import copy
import json
import jellyfish
import numpy as np
from loguru import logger

from framework.selection.Coverage import CoverageConverter

class GroundRanker:

    def __init__(self, corpus_file: str, weight: float = 0.5):
        self._corpus_file = corpus_file

        self._gt_coverage = []
        self._prev_coverage_success = []
        self._rest_coverage_success = []
        self._prev_coverage_fail = []
        self._rest_coverage_fail = []

        if 0 <= weight <= 1:
            self._weight = weight
        else:
            raise KeyError('weight must be in [0, 1]')

        self._coverage_converter = CoverageConverter()
        self._initialization()

    def _initialization(self):
        # load file
        with open(self._corpus_file, 'r') as f:
            data = json.load(f)

        # load type
        self._coverage_converter.load(data)

        self._gt_coverage = []
        for item in data['BF']:
            number_cov, str_cov = self._coverage_converter.get(item)
            self._gt_coverage.append({
                'element': item,
                'num_cov': number_cov,
                'str_cov': str_cov,
                'sim': np.inf
            })

        for item in data['BF']:
            logger.debug(item)

        self._prev_coverage_fail = []
        self._prev_coverage_success = []

        self._rest_coverage_success = []
        for item in data['AS']:
            number_cov, str_cov = self._coverage_converter.get(item)
            self._rest_coverage_success.append({
                'element': item,
                'num_cov': number_cov,
                'str_cov': str_cov,
                'sim': np.inf
            })

        self._rest_coverage_fail = []
        for item in data['AF']:
            number_cov, str_cov = self._coverage_converter.get(item)
            self._rest_coverage_fail.append({
                'element': item,
                'num_cov': number_cov,
                'str_cov': str_cov,
                'sim': np.inf
            })

    def _update(self):
        # load file todo: check and update
        with open(self._corpus_file, 'r') as f:
            data = json.load(f)

        for item in self._gt_coverage:
            number_cov, str_cov = self._coverage_converter.get(item['element'])
            item['num_cov'] = number_cov
            item['str_cov'] = str_cov
            item['sim'] = np.inf

        for item in self._rest_coverage_success:
            number_cov, str_cov = self._coverage_converter.get(item['element'])
            item['num_cov'] = number_cov
            item['str_cov'] = str_cov
            item['sim'] = np.inf

        for item in data['AS']:
            number_cov, str_cov = self._coverage_converter.get(item)
            self._rest_coverage_success.append({
                'element': item,
                'num_cov': number_cov,
                'str_cov': str_cov,
                'sim': np.inf
            })

        for item in self._rest_coverage_fail:
            number_cov, str_cov = self._coverage_converter.get(item['element'])
            item['num_cov'] = number_cov
            item['str_cov'] = str_cov
            item['sim'] = np.inf

        for item in data['AF']:
            number_cov, str_cov = self._coverage_converter.get(item)
            self._rest_coverage_fail.append({
                'element': item,
                'num_cov': number_cov,
                'str_cov': str_cov,
                'sim': np.inf
            })

    def selection(self, top_k: int, update: bool):
        if update:
            self._update()

        self._rank_success()
        self._rank_fail()

        select_fail = copy.deepcopy(self._rest_coverage_fail[:top_k])
        select_success = copy.deepcopy(self._rest_coverage_success[:top_k])

        self._prev_coverage_fail += select_fail
        self._prev_coverage_success += select_success

        fail_parameters = [item['element'] for item in select_fail]
        success_parameters = [item['element'] for item in select_success]

        return success_parameters, fail_parameters

    def _rank_success(self):
        for query_item in self._rest_coverage_success:
            min_prev_sim = np.inf
            for support_item in self._prev_coverage_success:
                prev_sim = self._similarity(query_item, support_item)
                if prev_sim < min_prev_sim:
                    min_prev_sim = prev_sim
            min_gt_sim = np.inf
            for support_item in self._gt_coverage:
                gt_sim = self._similarity(query_item, support_item)
                if gt_sim < min_gt_sim:
                    min_gt_sim = gt_sim

            query_sim = min_gt_sim - min_prev_sim
            query_item['sim'] = query_sim

        self._rest_coverage_success = sorted(self._rest_coverage_success, key=lambda k: k['sim'], reverse=False)

    def _rank_fail(self):
        for query_item in self._rest_coverage_fail:
            min_prev_sim = np.inf
            for support_item in self._prev_coverage_fail:
                prev_sim = self._similarity(query_item, support_item)
                if prev_sim < min_prev_sim:
                    min_prev_sim = prev_sim
            min_gt_sim = np.inf
            for support_item in self._gt_coverage:
                gt_sim = self._similarity(query_item, support_item)
                if gt_sim < min_gt_sim:
                    min_gt_sim = gt_sim

            query_sim = min(min_gt_sim, min_prev_sim)
            query_item['sim'] = query_sim

        self._rest_coverage_fail = sorted(self._rest_coverage_fail, key=lambda k: k['sim'], reverse=False)

    def _similarity(self, query, support):
        number_sim = self._number_similarity(query, support)
        string_sim = self._string_similarity(query, support)

        return self._weight * number_sim + (1 - self._weight) * string_sim

    @staticmethod
    def _number_similarity(query, support):
        # @: current is l1-norm
        return np.linalg.norm(np.array(query['num_cov']) - np.array(support['num_cov']), ord=1)

    @staticmethod
    def _string_similarity(query, support):
        # @: current is damerau_levenshtein_distance
        assert len(query['str_cov']) == len(support['str_cov'])

        str_sim = []
        for i in range(len(query['str_cov'])):
            query_i = query['str_cov'][i]
            suppo_i = support['str_cov'][i]
            str_dist = jellyfish.damerau_levenshtein_distance(query_i, suppo_i)
            str_sim.append(str_dist)

        return np.mean(np.array(str_sim))


if __name__ == '__main__':
    file_path = '/Users/Desktop/PhD/Conferences/2024-FSE/ChatFuzz/projects/ChatARP/data/Cases/Lang-12.json'
    cc = GroundRanker(file_path)

    a_succ, a_fail = cc.selection(4, False)

    logger.info(a_succ)
    logger.info(a_fail)

    a_succ, a_fail = cc.selection(4, False)

    logger.info(a_succ)
    logger.info(a_fail)