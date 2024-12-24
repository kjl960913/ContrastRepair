import json
import os

from loguru import logger
from dataclasses import dataclass

@dataclass
class BuggyRecord:

    id: str = '' # buggy id
    func_name: str ='' # buggy func name
    type: str = '' # error types
    command: str = ''  # testing command
    hash: int = 0

    d4j_initial: str = '' # parent folder of d4j initial
    d4j_verify: str = ''
    d4j_chat: str = ''

    # buggy func
    buggy_func_package: str = ''
    buggy_func_file_path: str = ''
    buggy_func_method_name: str = ''
    buggy_func_start_line: int = 0
    buggy_func_end_line: int = 0

    # lib
    lib_package: str = ''
    # tmp
    tmp_folder: str = ''
    buggy_instrument: bool = False
    verify_command_file: str = ''
    verify_log: str = ''

    # test case
    test_case_package: str = ''
    test_case_file_path: str = ''
    test_case_method_name: str = ''
    test_case_error_line: int = -1

    # save results
    BF: str = ''
    BS: str = ''
    AS: str = ''
    AF: str = ''
    # mutation
    mutation: str = ''

    # flag
    has_found_test: bool = False
    has_found_buggy: bool = False

    @staticmethod
    def get_one(idx, func_name):
        return BuggyRecord(idx, func_name)


    def get_one_from_json(self, json_file):
        with open(json_file, 'r') as f:
            json_data = json.load(f)
        for k, v in self.__dict__.items():
            if k in json_data.keys():
                self.__dict__[k] = json_data[k]

    def update_initial_stage(self, d4j_folder, buggy_func_name):
        logger.debug(buggy_func_name)
        fail_file = os.path.join(d4j_folder, 'failing_tests')

        if not os.path.exists(fail_file):
            raise RuntimeError()

        self.d4j_initial = d4j_folder

        self.buggy_func_package = os.popen('defects4j export -w %s -p dir.bin.classes' % d4j_folder).readlines()[-1].split(':')[-1]
        self.test_case_package = os.popen('defects4j export -w %s -p dir.bin.tests' % d4j_folder).readlines()[-1].split(':')[-1]
        self.lib_package = self.test_case_package

        class_parent_dir = os.path.dirname(os.path.join(d4j_folder, self.test_case_package))

        other_libs_name = os.listdir(class_parent_dir)
        if len(other_libs_name) > 2:
            for item in other_libs_name:
                item_path = '/'.join(self.test_case_package.split('/')[:-1]) # os.path.join(class_parent_dir, item)
                item_path = os.path.join(item_path, item) # item_path.split('d4j_initial/')[1]
                if item_path == self.buggy_func_package \
                        or item_path == self.test_case_package:
                    continue
                elif 'lib' in item_path:
                    self.lib_package = item_path
                    break
        try:
            with open(fail_file, "r") as f:
                text = f.read()
        except:
            with open(fail_file, "r", encoding='ISO-8859-1') as f:
                text = f.read()

        if len(text.split("--- ")) >= 2:
            # error_string = text[1]
            x = text.split("--- ")[1]  # just grab first one
            self.command =  x.splitlines()[0]

            if 'Exception' in x.splitlines()[1]:
                error_type = 'Exception'
            else:
                error_type = 'Assertion'

            self.type = error_type

            if len(self.command.split("::")) > 1:
                for line in x.splitlines()[1:]:
                    # if test_method_name in line:
                    try:
                        test_class_name = line.split("(")[1].split(")")[0].split(':')[0].split('.')[0]  # line.split(":")[-1].split(")")[0]
                        test_error_line_number = line.split("(")[1].split(")")[0].split(':')[1]
                        test_class_line = line.split("(")[0].split("at ")[1]
                        if '<' in test_class_line or '>' in test_class_line or '$' in test_class_line:
                            continue
                        # logger.debug()
                        test_class_elements = test_class_line.split('.')
                        test_class_file_rel_path = []
                        for item in test_class_elements:
                            if item.strip() != test_class_name.strip():
                                test_class_file_rel_path.append(item)
                            else:
                                test_class_file_rel_path.append(item)
                                break

                        test_class_file_rel_path = '/'.join(test_class_file_rel_path)
                        test_class_file_path = os.path.join(d4j_folder,
                                                            self.test_case_package,
                                                            test_class_file_rel_path + '.class')
                        if os.path.isfile(test_class_file_path):
                            self.test_case_error_line = int(test_error_line_number)
                            self.test_case_file_path =os.path.join(self.test_case_package, test_class_file_rel_path + '.class')
                            self.test_case_method_name = test_class_elements[-1]
                            self.has_found_test = True
                            break
                    except IndexError:
                        pass

                for line in x.splitlines()[2:]:
                    try:
                        buggy_class_file_name = line.split("(")[1].split(")")[0].split(':')[0].split('.')[0]
                        buggy_error_line = line.split("(")[1].split(")")[0].split(':')[1]
                        buggy_class_line = line.split("(")[0].split("at ")[1]
                        if '<' in buggy_class_line or '>' in buggy_class_line or '$' in buggy_class_line:
                            continue
                        buggy_class_elements = buggy_class_line.split('.')
                        extract_buggy_func_name = buggy_class_elements[-1]

                        logger.debug(line)
                        logger.debug('extract_buggy_func_name {}, buggy_func_name {}', extract_buggy_func_name, buggy_func_name)
                        if extract_buggy_func_name.lower() != buggy_func_name.lower():
                            continue

                        buggy_class_file_rel_path = []
                        for item in buggy_class_elements:
                            if item.strip() != buggy_class_file_name.strip():
                                buggy_class_file_rel_path.append(item)
                            else:
                                buggy_class_file_rel_path.append(item)
                                break
                        buggy_class_file_rel_path = '/'.join(buggy_class_file_rel_path)
                        buggy_class_file_path = os.path.join(d4j_folder,
                                                             self.buggy_func_package,
                                                             buggy_class_file_rel_path + '.class')

                        # logger.info(buggy_class_file_path)
                        if os.path.isfile(buggy_class_file_path):
                            self.buggy_func_error_line = int(buggy_error_line)
                            self.buggy_func_file_path = os.path.join(self.buggy_func_package, buggy_class_file_rel_path + '.class')
                            self.buggy_func_method_name = buggy_func_name
                            self.has_found_buggy = True
                            break
                    except IndexError:
                        pass
