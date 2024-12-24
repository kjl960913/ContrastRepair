import numpy as np

class CoverageConverter:
    number_types = ["int", "short", "float", "byte", "double", "boolean", "long", "char"]#, "hex"]
    string_types = ["char[]", "string[]", "string"]
    array_types = ["int[]"]
    def __init__(self):
        self._types = []
        self._types_ranges = {}
        self._allow_types = self.number_types + self.string_types

        self._str_indexes = []
        self._num_indexes = []
        self._loaded = False

    def load(self, data):
        tmp_data = data['BF'] + data['AS'] #+ data['AF']

        if not self._loaded:
            if 'Type' in data:
                self._types = data['Type']
            if 'type' in data:
                self._types = data['type']
            # print(self._types)
            hex_dict = {}
            for case in tmp_data:
                for i in range(len(case)):
                    if self._types[i].lower() in self.number_types:
                        self._num_indexes.append(i)
                    elif self._types[i].lower() in self.string_types:
                        self._str_indexes.append(i)
                        # try:
                        #     _ = int(case[i], 16)
                        #     case_hex = True
                        # except ValueError as e:
                        #     case_hex = False

                        # if case_hex:
                        #     if i not in hex_dict.keys():
                        #         hex_dict[i] = True
                        #     else:
                        #         if not hex_dict[i]:
                        #             hex_dict[i] = False
                        # else:
                        #     self._str_indexes.append(i)
                        #     if i not in hex_dict.keys():
                        #         hex_dict[i] = False
                        #     else:
                        #         hex_dict[i] = False
                    else:
                        # print(self._types[i].lower())
                        continue

            # for k, v in hex_dict.items():
            #     if v:
            #         self._types[k] = 'hex'
            #         self._num_indexes.append(k)

            self._num_indexes = list(set(self._num_indexes))
            self._str_indexes = list(set(self._str_indexes))

        # type range
        num_array = []
        num_array_index = []
        for case in tmp_data:
            case_num = []
            for i in range(len(case)):
                if i not in self._num_indexes:
                    continue
                case_num.append(self._number_converter(self._types[i], case[i]))
                if i not in num_array_index:
                    num_array_index.append(i)
            num_array.append(case_num)

        if len(num_array) > 0:
            num_array = np.array(num_array)
            num_array_max = np.max(num_array, axis=0)
            num_array_min = np.min(num_array, axis=0)
        else:
            num_array_min = 0.0
            num_array_max = 0.0 + 1e-5

        for i in num_array_index:
            if i not in self._types_ranges.keys():
                self._types_ranges[i] = [num_array_min[i], num_array_max[i]]
            else:
                min_value = min(self._types_ranges[i][0], num_array_min[i])
                max_value = max(self._types_ranges[i][1], num_array_max[i])
                self._types_ranges[i] = [min_value, max_value]

    @staticmethod
    def _number_converter(p_type, p_value):
        if p_type.lower() == 'boolean':
            if p_value.lower() == 'false':
                return 0
            else:
                return 1
        elif p_type.lower() == 'long':
            p_value = p_value.replace('L', '')
            return p_value
        elif p_type.lower() == 'char':
            return ord(p_value)
        elif p_type.lower() == 'hex':
            return int(p_value, 16)
        else:
            return float(p_value)

    @staticmethod
    def _string_converter(p_type, p_value):
        return str(p_value)

    @staticmethod
    def _array_converter(p_type, p_value):
        pass

    def _number_norm(self, p_index, p_value):
        p_min = self._types_ranges[p_index][0]
        p_max = self._types_ranges[p_index][1]

        if p_max > (p_min + 1e-5):
            p_norm = (p_value - p_min) / float(p_max - p_min)
        else:
            p_norm = 0
        return p_norm

    def get(self, case):
        case_number_vector = []
        case_string_vector = []
        for i in range(len(case)):
            p_type = self._types[i]
            p_value = case[i]
            if i in self._num_indexes:
                p_value = self._number_converter(p_type, p_value)
                case_number_vector.append(self._number_norm(i, p_value))
            elif i in self._str_indexes:
                p_value = self._string_converter(p_type, p_value)
                case_string_vector.append(p_value)
            else:
                continue

        return case_number_vector, case_string_vector