import glob
import os
import json
from difflib import unified_diff
from loguru import logger


def remove_suffix(input_string, suffix):
    if suffix and input_string.endswith(suffix):
        return input_string[:-len(suffix)]
    return input_string


def remove_prefix(input_string, prefix):
    if prefix and input_string.startswith(prefix):
        return input_string[len(prefix):]
    return input_string


def check_d4j_2(bug, d4j_2=False):
    is_d4j_2 = True
    if 'Time' in bug or 'Math' in bug or 'Mockito' in bug or 'Chart' in bug or 'Lang' in bug:
        is_d4j_2 = False
    elif 'Closure' in bug:
        if int(bug.split(".java")[0].split("-")[-1]) <= 133:
            is_d4j_2 = False

    return is_d4j_2 == d4j_2


def get_unified_diff(source, mutant):
    output = ""
    for line in unified_diff(source.split('\n'), mutant.split('\n'), lineterm=''):
        output += line + "\n"
    return output


class Defects4j12:

    @staticmethod
    def get_data(folder, sub_type='LANG', specific_type=(), single_hunk=False, single_line=False):
        if single_hunk:
            file = "single_function_single_hunk_repair"
        elif single_line:
            file = "single_function_single_line_repair"
        else:
            file = "single_function_repair"
        with open(os.path.join(folder, "failing_test_info.json"), "r") as f:
            failing_test_info = json.load(f)
        with open(os.path.join(folder, "{}.json".format(file)), "r") as f:
            result = json.load(f)

        cleaned_result = {}
        buggy_info = {}
        for k, v in result.items():
            if len(specific_type) > 0:
                is_sp = False
                for sp in specific_type:
                    if sp.lower() == k.lower():
                        is_sp = True
                        break
                if not is_sp:
                    continue

            if sub_type.lower() != 'all':
                k_pref = k.split('-')[0]
                if k_pref.lower() != sub_type.lower():
                    continue
            if file == "single_function_repair":
                buggy_info[k] = {
                    'func_name': v['buggy_fun_name'],
                    'start_line': v['start'],
                    'end_line': v['end']
                }
            else:
                buggy_info[k] = {
                    'start_line': v['start'],
                    'end_line': v['end']
                }
            lines = v['buggy'].splitlines()
            leading_white_space = len(lines[0]) - len(lines[0].lstrip())
            cleaned_result[k + ".java"] = v
            cleaned_result[k + ".java"]["buggy"] = "\n".join([line[leading_white_space:] for line in lines])
            lines = v['fix'].splitlines()
            leading_white_space = len(lines[0]) - len(lines[0].lstrip())
            cleaned_result[k + ".java"]["fix"] = "\n".join([line[leading_white_space:] for line in lines])
            if k + ".java" in failing_test_info:
                cleaned_result[k + ".java"]["failing_tests"] = failing_test_info[k + ".java"]['failing_tests']
            if "prefix" in v:
                lines = v["prefix"].splitlines()
                cleaned_result[k + ".java"]["prefix"] = "\n".join([line[leading_white_space:] for line in lines])
                lines = v["suffix"].splitlines()
                cleaned_result[k + ".java"]["suffix"] = "\n".join([line[leading_white_space:] for line in lines])
                cleaned_result[k + ".java"]["buggy_line"] = remove_suffix(
                    remove_prefix(cleaned_result[k + ".java"]["buggy"], cleaned_result[k + ".java"]["prefix"]),
                    cleaned_result[k + ".java"]["suffix"]).strip()
                cleaned_result[k + ".java"]["correct_line"] = remove_suffix(
                    remove_prefix(cleaned_result[k + ".java"]["fix"], cleaned_result[k + ".java"]["prefix"]),
                    cleaned_result[k + ".java"]["suffix"]).strip()

        result = {k: v for k, v in cleaned_result.items() if check_d4j_2(k, False)}  # Default is False

        logger.info('Defects4j12: {}', result.keys())

        return result, buggy_info

    @staticmethod
    def parse_defects4j_2(folder):
        file = "single_function_single_line_repair"
        with open(os.path.join(folder, "failing_test_info.json"), "r") as f:
            failing_test_info = json.load(f)
        with open(os.path.join(folder, "{}.json".format(file)), "r") as f:
            result = json.load(f)
        cleaned_result = {}
        for k, v in result.items():
            lines = v['buggy'].splitlines()
            leading_white_space = len(lines[0]) - len(lines[0].lstrip())
            cleaned_result[k + ".java"] = v
            cleaned_result[k + ".java"]["buggy"] = "\n".join([line[leading_white_space:] for line in lines])
            lines = v['fix'].splitlines()
            leading_white_space = len(lines[0]) - len(lines[0].lstrip())
            cleaned_result[k + ".java"]["fix"] = "\n".join([line[leading_white_space:] for line in lines])
            if k + ".java" in failing_test_info:
                cleaned_result[k + ".java"]["failing_tests"] = failing_test_info[k + ".java"]['failing_tests']
            if "prefix" in v:
                lines = v["prefix"].splitlines()
                cleaned_result[k + ".java"]["prefix"] = "\n".join([line[leading_white_space:] for line in lines])
                lines = v["suffix"].splitlines()
                cleaned_result[k + ".java"]["suffix"] = "\n".join([line[leading_white_space:] for line in lines])
                cleaned_result[k + ".java"]["buggy_line"] = remove_suffix(
                    remove_prefix(cleaned_result[k + ".java"]["buggy"], cleaned_result[k + ".java"]["prefix"]),
                    cleaned_result[k + ".java"]["suffix"]).strip()
                cleaned_result[k + ".java"]["correct_line"] = remove_suffix(
                    remove_prefix(cleaned_result[k + ".java"]["fix"], cleaned_result[k + ".java"]["prefix"]),
                    cleaned_result[k + ".java"]["suffix"]).strip()
        result = {k: v for k, v in cleaned_result.items() if check_d4j_2(k, True)}

        return result


class QuixBugs:
    @staticmethod
    def parse_python():
        folder = os.getcwd() + '/'
        with open(os.path.join(folder, 'QuixBugs/fault_location/QuixBugs_Python_info.json'), 'r') as f:
            ret = json.load(f)
        return ret

    @staticmethod
    def parse_java():
        folder = os.getcwd()
        with open(os.path.join(folder, 'QuixBugs/fault_location/QuixBugs_Java_info.json'), 'r') as f:
            ret = json.load(f)
        return ret
