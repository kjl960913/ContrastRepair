import json
import random
import numpy as np
import jellyfish

from loguru import logger
class AssertRanker:

    def __init__(self, assert_file: str,
                 pair_prob_fail: float = 0.5,
                 pair_prob_succ: float = 0.5):
        self._assert_file = assert_file

        self._BF = []
        self._BS = []
        self._population = []

        if self._assert_file is not None:
            self._initialization()

    def _initialization(self):
        # load file
        with open(self._assert_file, 'r') as f:
            data = json.load(f)

        self._BS = []
        self._BF = []

        for item in data['BS']:
            self._BS.append({
                'element': item,
                'type': 'Assert'
            })

        for item in data['BF']:
            self._BF.append({
                'element': item,
                'type': 'Assert',
                'as_prev': [],
                'as_rest': list(range(len(self._BS)))
            })

    def _update(self):
        with open(self._assert_file, 'r') as f:
            data = json.load(f)

        for item in data['BS']:
            self._BS.append({
                'element': item,
                'type': 'Assert'
            })

        for item in data['BF']:
            self._BF.append({
                'element': item,
                'type': 'Assert',
                'as_prev': [],
                'as_rest': list(range(len(self._BS)))
            })

        for item in self._BF:
            item['as_rest'] = list(range(len(self._BS)))

    def _reset(self):

        for item in self._BF:
            item['as_prev'] = []
            item['as_rest'] = list(range(len(self._BS)))

    def selection(self, pairs: int, top_k: int, update: bool, reset: bool):
        if len(self._BS) == 0 and len(self._BF) == 0:
            return []

        # @ todo: add probability
        if update:
            self._update()

        if reset:
            self._reset()

        if pairs > len(self._BF):
            logger.warning('Setting pairs {} is larger than BF number {}', pairs, len(self._BF))
            pairs = len(self._BF)

        select_fails = [0] #random.sample(range(len(self._BF)), pairs)
        select_pairs = []
        for sf_index in select_fails:
            sf = self._BF[sf_index]
            logger.debug('prev {}:{}/{} : {}', sf_index, len(sf['as_prev']), len(sf['as_rest']), sf['as_prev'])
            # logger.debug('rest {}:{}', sf_index, len(sf['as_rest']))
            if len(sf['as_prev']) == len(sf['as_rest']):
                # select random
                sf_sort_lst = random.sample(sf['as_rest'], pairs)
            else:
                sf_sort_lst = self._rank(sf)
                sf_sort_lst = sf_sort_lst[:top_k]
            logger.debug(sf_sort_lst)
            select_pairs.append({
                'fail': self._BF[sf_index]['element'],
                'success': [self._BS[as_i[0]]['element'] for as_i in sf_sort_lst],
                'type': 'Assert'
            })
            for as_i in sf_sort_lst:
                self._BF[sf_index]['as_prev'].append(as_i[0])
            self._BF[sf_index]['as_prev'] = list(set(self._BF[sf_index]['as_prev']))
            logger.debug(self._BF[sf_index]['as_prev'])

        return select_pairs

    def _rank(self, BF):
        tmp_sim = []
        for as_rest_index in BF['as_rest']:
            bf_sim = self._similarity(BF, self._BS[as_rest_index]) # min is good
            min_prev_sim = np.inf
            for as_prev_index in BF['as_prev']:
                prev_sim = self._similarity(self._BS[as_prev_index], self._BS[as_rest_index])
                if prev_sim < min_prev_sim:
                    min_prev_sim = prev_sim # @todo: modify this -> related to the select frequency

            if len(BF['as_prev']) == 0:
                min_prev_sim = 0.0 # max is better

            sim = bf_sim - min_prev_sim
            tmp_sim.append([as_rest_index, sim, self._BS[as_rest_index]['element']])

        # min is better
        tmp_sim = sorted(tmp_sim, key=lambda k: k[1])
        logger.debug(tmp_sim)
        return tmp_sim

    def _similarity(self, query, support):
        # @: current is damerau_levenshtein_distance
        assert len(query['element']) == len(support['element'])
        str_sim = []
        for i in range(len(query['element'])):
            query_i = query['element'][i]
            suppo_i = support['element'][i]
            str_dist = jellyfish.damerau_levenshtein_distance(query_i, suppo_i)
            str_sim.append(str_dist)

        if len(str_sim) > 0:
            return np.mean(np.array(str_sim))
        else:
            return 0.0
