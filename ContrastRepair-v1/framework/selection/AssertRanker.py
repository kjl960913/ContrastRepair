import copy
import json
import random
import numpy as np
import jellyfish

from loguru import logger
class AssertRanker:
    def __init__(self, assert_file: str,
                 pair_prob_fail: float = 0.5,
                 pair_prob_succ: float = 0.5,
                 penalty: float = 1.0):
        self._assert_file = assert_file

        self._BF = []
        self._BS = []
        self._population = []
        self._population_index = []
        self._rest_index = []

        self._pair_prob_fail = pair_prob_fail  # node
        self._pair_prob_succ = pair_prob_succ  # leaf
        self._penalty = penalty

        if self._assert_file is not None:
            self._load_data()

    def _load_data(self):
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
                'selection': dict(),
                'population': list()
            })

    def _initialization(self, pairs, top_k):
        self._population = []
        self._rest_index = list(range(len(self._BF)))
        self._population_index = random.sample(list(range(len(self._BF))), pairs)
        for sf_index in self._population_index:
            self._population.append(copy.deepcopy(self._BF[sf_index]))
            self._rest_index.remove(sf_index)

        current_leaf_indexes = []
        for pop_item in self._population:
            pop_item['population'] = list()
            pop_item_top_k = self._select_top_k(pop_item, top_k, current_leaf_indexes)
            # update pop item info
            for as_i in pop_item_top_k:
                as_i_index = as_i[0]
                if as_i_index in pop_item['selection'].keys():
                    pop_item['selection'][as_i_index] += 1
                else:
                    pop_item['selection'][as_i_index] = 0
                pop_item['population'].append(as_i_index)
                current_leaf_indexes.append(as_i_index)

    def _select_top_k(self, pair_ref, top_k, current_leaf_indexes):
        tmp_sim = []
        for i in range(len(self._BS)):
            if i in current_leaf_indexes:
                continue
            pair_bs = self._BS[i]
            pair_sim = self._similarity(pair_ref, pair_bs)

            if i in pair_ref['selection'].keys():
                # select time * penalty
                pair_sim += pair_ref['selection'][i] * self._penalty

            tmp_sim.append((i, pair_sim))

        tmp_sim = sorted(tmp_sim, key=lambda k: k[1])
        return tmp_sim[:top_k]

    def _select_no_repeat_top_1(self, pair_ref, current_leafs):
        tmp_sim = []
        for i in range(len(self._BS)):
            if i in current_leafs:
                continue
            pair_bs = self._BS[i]
            pair_sim = self._similarity(pair_ref, pair_bs)
            if i in pair_ref['selection'].keys():
                # select time * penalty
                pair_sim += pair_ref['selection'][i] * self._penalty
            tmp_sim.append((i, pair_sim))
        if len(tmp_sim) > 0:
            tmp_sim = sorted(tmp_sim, key=lambda k: k[1])
            return tmp_sim[:1]
        else:
            return []

    def _mutation_pair_node(self, curr_node_index, top_k, current_leaf_indexes):
        pop_item = copy.deepcopy(self._BF[curr_node_index])
        for i in pop_item['population']:
            current_leaf_indexes.remove(i)
        pop_item['population'] = list()
        pop_item_top_k = self._select_top_k(pop_item, top_k, current_leaf_indexes)
        # update pop item info
        for as_i in pop_item_top_k:
            as_i_index = as_i[0]
            if as_i_index in pop_item['selection'].keys():
                pop_item['selection'][as_i_index] += 1
            else:
                pop_item['selection'][as_i_index] = 0
            pop_item['population'].append(as_i_index)
            current_leaf_indexes.append(as_i_index)
        return pop_item, current_leaf_indexes

    def _mutation_pair_leaf(self, pop_item, current_leaf_indexes):
        leaf_population = pop_item['population']
        for i in range(len(leaf_population)):
            if random.random() > self._pair_prob_succ:
                prev_bs_i_index = leaf_population[i]
                logger.debug(current_leaf_indexes)
                # todo: fix bugs
                bs_i = self._select_no_repeat_top_1(pop_item, current_leaf_indexes)[0]
                bs_i_index = bs_i[0]
                pop_item['population'][i] = bs_i_index # index
                if bs_i_index in pop_item['selection'].keys():
                    pop_item['selection'][bs_i_index] += 1
                else:
                    pop_item['selection'][bs_i_index] = 0
                current_leaf_indexes.remove(prev_bs_i_index)
                current_leaf_indexes.append(bs_i_index)
        return pop_item, current_leaf_indexes

    def _build_output(self):
        select_pairs = {
            'type': 'Assert',
            'fail': [],
            'success': []
        }
        for node_item in self._population:
            select_pairs['fail'].append(node_item['element'])
            for leaf_item_index in node_item['population']:
                select_pairs['success'].append(self._BS[leaf_item_index]['element'])

        return select_pairs

    def selection(self, pairs: int, top_k: int):
        # @ todo: add probability

        if len(self._BF) == 0 and len(self._BS) == 0:
            return {
            'type': 'Assert',
            'fail': [],
            'success': []
        }

        if pairs >= len(self._BF):
            logger.warning('Setting pairs {} is larger than BF number {}', pairs, len(self._BF))
            pairs = len(self._BF)


        if top_k >= len(self._BS):
            logger.warning('Setting top k {} is larger than BS number {}', top_k, len(self._BS))
            top_k = len(self._BS)

        if len(self._population) == 0:
            # @ todo: select population
            self._initialization(pairs, top_k)
            return self._build_output()

        self._rest_index = list(range(len(self._BF)))
        for node_index in self._population_index:
            self._rest_index.remove(node_index)

        current_leaf_indexes = []
        for pop_item in self._population:
            current_leaf_indexes += pop_item['population']
        current_leaf_indexes = list(set(current_leaf_indexes))

        if len(self._rest_index) > 0:
            for i in range(len(self._population)):
                pop_index = self._population_index[i]
                if random.random() > self._pair_prob_fail:
                    new_pop_index = random.sample(self._rest_index, 1)[0]
                    new_pop_item, current_leaf_indexes = self._mutation_pair_node(new_pop_index, top_k, current_leaf_indexes)
                    self._population[i] = new_pop_item
                    self._population_index[i] = new_pop_index
                    # update rest_index
                    self._rest_index.append(pop_index)
                    self._rest_index.remove(new_pop_index)

            for p_i in range(len(self._population)):
                pop_item = self._population[p_i]
                leaf_population = pop_item['population']
                for i in range(len(leaf_population)):
                    if random.random() > self._pair_prob_succ:
                        pop_item, current_leaf_indexes = self._mutation_pair_leaf(pop_item, current_leaf_indexes)
                        self._population[p_i] = pop_item

        return self._build_output()

    def _similarity(self, query, support):
        # @: current is damerau_levenshtein_distance
        # assert len(query['element']) == len(support['element'])
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
