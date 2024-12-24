# -*- coding: utf-8 -*-

import json
import os
import subprocess
import re
import sys
import traceback

print("this is testcase_mining3!!!")
os.environ["JAVA_HOME"] = "/root/jdk1.8.0_371"
os.environ['PATH'] += ':/root/defects4j/framework/bin'
buggy_project_dir = '/tmp/record_testcases_for_buggy_functions'
bugid = sys.argv[1]
wo_contextual_code = sys.argv[2]

# Rest of your code that uses bugid
prlist = [bugid.split("-")[0]]
# print("prlist is ", prlist)
ids = [int(bugid.split("-")[1])]
# project_plus_bugid = f"{prlist[0]}{ids[0]}"
project_plus_bugid = prlist[0] + str(ids[0])
project_plus_bugid = 'buggy'+ project_plus_bugid
buggy_project_path = buggy_project_dir + '/' + project_plus_bugid
repo_from_github = "/root/defects4j/framework/projects"
# patch_file_path = f"{repo_from_github}/{prlist[0]}/patches/{ids[0]}.src.patch"
patch_file_path = repo_from_github+'/'+prlist[0]+'/'+'patches'+'/'+str(ids[0])+'.src.patch'
print("patch_file_path: ", patch_file_path)

def extract_function_name(function_code):
    param_pattern = r"\b(public|private|protected|static)?\s+(abstract\s+)?\w+\s+(\w+)\s*\(([\w\s,<>\[\]]*)\)\s*(throws [\w\s,.]+)?\s*\{"
    match = re.search(param_pattern, function_code)
    if not match:
        return None
    else:
        # visibility = match.group(1)
        # is_abstract = match.group(2)
        function_name = match.group(3)
        # param_str = match.group(4)
    return function_name

def create_buggy_projects(current_buggy_project_path):
    if os.path.exists(current_buggy_project_path):
        os.system(f'rm -rf {current_buggy_project_path}')

    cmd_checkout_buggy_dir = f'defects4j checkout -p {prlist[0]} -v {ids[0]}b -w {current_buggy_project_path}'
    os.system(cmd_checkout_buggy_dir)

def find_buggy_classes(current_buggy_project_path):
    cmd_export_modified_classes_information = f'defects4j export -p classes.modified -w {current_buggy_project_path}'

    # result_modified_classes_information = os.popen(cmd_export_modified_classes_information).readlines()
    process = subprocess.Popen(cmd_export_modified_classes_information.split(), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    feedback_result = stdout.decode("utf-8")
    result_modified_classes_information = feedback_result.split('\n')
    lens = len(result_modified_classes_information)
    print(result_modified_classes_information, f"There are {lens} element(s)")
    # Kill the process
    process.kill()

    return result_modified_classes_information

def find_buggy_dir4buggy_classes(current_buggy_project_path):
    # ['src/main/java']
    cmd_export_src_dir_path = f'defects4j export -p dir.src.classes -w {current_buggy_project_path}'
    # result_src_dir_information = os.popen(cmd_export_src_dir_path).readlines()
    process = subprocess.Popen(cmd_export_src_dir_path.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    feedback_result = stdout.decode("utf-8")
    result_src_dir_information = feedback_result.split('\n')
    lens = len(result_src_dir_information)
    print(result_src_dir_information, f"There are {lens} element(s)")
    # Kill the process
    process.kill()

    return result_src_dir_information

def find_dir4test_class(current_buggy_project_path):
    # ['src/test/java']
    cmd_export_testclass_dir_path = f'defects4j export -p dir.src.tests -w {current_buggy_project_path}'
    # result_testclass_dir_information = os.popen(cmd_export_testclass_dir_path).readlines()
    process = subprocess.Popen(cmd_export_testclass_dir_path.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    feedback_result = stdout.decode("utf-8")
    result_testclass_dir_information = feedback_result.split('\n')
    lens = len(result_testclass_dir_information)
    print(result_testclass_dir_information, f"There are {lens} element(s)")
    # Kill the process
    process.kill()
    return result_testclass_dir_information

def find_trigger_path(current_buggy_project_path):
    # ['org.apache.commons.cli.ValueTest::testPropertyOptionFlags']
    cmd_export_test_trigger_information = f'defects4j export -p tests.trigger -w {current_buggy_project_path}'
    # result_test_trigger_information = os.popen(cmd_export_test_trigger_information).readlines()
    process = subprocess.Popen(cmd_export_test_trigger_information.split(), stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()
    feedback_result = stdout.decode("utf-8")
    result_test_trigger_information = feedback_result.split('\n')
    lens = len(result_test_trigger_information)
    print(result_test_trigger_information, f"There are {lens} element(s)")
    # Kill the process
    process.kill()
    return result_test_trigger_information

def construct_file_complete_path(project_plus_bugid, dir_list4modified_class,
                                 modified_class_path_list):
    modified_class_paths = []
    for dir in dir_list4modified_class:
        for path in modified_class_path_list:
            modified_class_path = f"{project_plus_bugid}/" + dir + "/" + path.replace('.', '/') + '.java'
            if os.path.exists(modified_class_path) and modified_class_path not in modified_class_paths:
                modified_class_paths.append(modified_class_path)

    return modified_class_paths

# combine the source code of buggy functions and the correct code snippets
def combine_source_code_of_buggy_and_correct(dict_modified_classes_with_no_buggyfunc, modified_buggy_funcs):
    # after buggyfunction extracting，insert source_code_without_buggy_functions
    modified_classes = dict_modified_classes_with_no_buggyfunc.keys()
    # class_num = len(modified_classes)
    current_buggyfunc_count = 0
    dict_modified_class_outputpatch = {}
    dict_modified_source_code_after_patch = {}
    try:
        for modified_class in modified_classes:
            correct_parts_str_list = dict_modified_classes_with_no_buggyfunc[modified_class]
            buggy_func_num = len(correct_parts_str_list) - 1
            print(f"{modified_class}need yo be inseted of {buggy_func_num} buggy function")
            dict_modified_class_outputpatch[modified_class] = modified_buggy_funcs[current_buggyfunc_count:
                                                                                              current_buggyfunc_count + buggy_func_num]
            source_code_after_patch = ""
            for i, correct_part_str in enumerate(correct_parts_str_list):
                # if i==0, means the first correct part, add the package needed to this part
                if i == 0:
                    lines = correct_part_str.split('\n')
                    for index, line in enumerate(lines):
                        lstr = line.strip()
                        if lstr.startswith('package'):
                            str_insert = "\nimport java.io.ObjectOutputStream;\nimport java.io.FileOutputStream;\nimport java.io.File;\nimport java.io.FilenameFilter;\nimport java.io.IOException;\n"
                            # print('\n'.join(lines[0:index]))
                            correct_part_str = '\n'.join(lines[0:index+1]) + \
                                               str_insert + '\n'.join(lines[index+1:])
                            break
                source_code_after_patch += correct_part_str
                if not i == len(correct_parts_str_list) - 1:
                    source_code_after_patch += dict_modified_class_outputpatch[modified_class][i]
            dict_modified_source_code_after_patch[modified_class] = source_code_after_patch
            current_buggyfunc_count = current_buggyfunc_count + buggy_func_num
        if not current_buggyfunc_count == len(modified_buggy_funcs):
            print(f"generate {len(modified_buggy_funcs)}, insert {current_buggyfunc_count}")
        else:
            print("outputing buggy func have been inserted to correct parts!")
        return dict_modified_class_outputpatch, dict_modified_source_code_after_patch
    except Exception as e:
        print(e)
        traceback.print_exc()

def write_modified_class_back_to_file(modified_classes_paths, dict_modified_sourcecode_after_patch):
    modified_classes = dict_modified_sourcecode_after_patch.keys()
    for modified_class in modified_classes:
        source_code_after_modified = dict_modified_sourcecode_after_patch[modified_class]
        for modified_class_path in modified_classes_paths:
            if modified_class in modified_class_path:
                with open(modified_class_path, 'w') as f:
                    f.write(source_code_after_modified)


def build_var_def_line_dict(test_class_lines, trigger_func, line_number):

    # get the test functions code lines
    start, end = 0, 0
    for inx, lin in enumerate(test_class_lines):
        if trigger_func in lin.strip():
            start = inx
            break
    countl, countr = 0, 0
    for inx, lin in enumerate(test_class_lines[start:]):
        countl += lin.count("{")
        countr += lin.count("}")
        if countl == countr > 0:
            end = start + inx
            break
    test_func_lines = test_class_lines[start+1:line_number-1]
    # test_func_lines = test_class_lines[start + 1:end]
    test_func_code  = "".join(test_func_lines)
    pattern = r"//.*?$"
    cleaned_code = re.sub(pattern, "", test_func_code, flags=re.MULTILINE)
    pattern = r"/\*.*?\*/"
    cleaned_code = re.sub(pattern, "", cleaned_code, flags=re.DOTALL)
    cleaned_code_lines = cleaned_code.split("\n")
    var_line_dict = {}
    vars = set()
    code = ""
    code_num = -1
    for line_num, line in enumerate(cleaned_code_lines):
        line = line.strip()
        if code != "":
            code += line
        else:
            code = line
            code_num = line_num
        if line.endswith(";"):
            if not code.startswith("assert") and not code.startswith("Assert"):
                code = code.strip()
                pattern = r"^\s*(final\s+)?[a-zA-Z_$][a-zA-Z0-9_$<>\[\]]*\s+[a-zA-Z_$][a-zA-Z0-9_$]*\s*(=\s*[^;]+)?\s*;$"
                match = re.match(pattern, code)
                if match:
                    equal_sign_index = code.find("=")
                    code_def = code[0:equal_sign_index]
                    # code_ref = code[equal_sign_index + 1:]
                    pattern = r"[a-zA-Z_$][a-zA-Z0-9_$]*"
                    words = re.findall(pattern, code_def)
                    def_var_name = words[-1]
                    vars.add(def_var_name)
                    var_line_dict[def_var_name] = []

                pattern = r"[a-zA-Z_$][a-zA-Z0-9_$]*"
                words = re.findall(pattern, code)
                first_word = ""
                for word in words:
                    if word in vars:
                        if first_word == "":
                            first_word = word
                            var_line_dict[word].append((code_num, code))
                        else:
                            for item in var_line_dict[word]:
                                # add by  6/13 solve infinite loop situation
                                if item not in var_line_dict[first_word]:
                                    var_line_dict[first_word].append(item)

        if line.endswith("}") or line.endswith("{") or line.endswith(";"):
            code = ""

    for var in var_line_dict.keys():
        var_line_dict[var] = sorted(var_line_dict[var], key=lambda x: x[0])
    return var_line_dict


def complete_def_code(buggy_line_code, var_def_line_dict):


    pattern = r"[a-zA-Z_$][a-zA-Z0-9_$]*"
    words = re.findall(pattern, buggy_line_code)
    def_lines = []
    for word in words:
        if word in var_def_line_dict.keys():
            def_lines.extend(var_def_line_dict[word])
    def_lines = sorted(def_lines, key=lambda x: x[0])
    var_first={}
    var_last={}
    vars = var_def_line_dict.keys()
    for line_num, line in def_lines:
        pattern = r"[a-zA-Z_$][a-zA-Z0-9_$]*"
        words = re.findall(pattern, line)
        first_word = ""
        for word in words:
            if word in vars:
                first_word = word
                break
        if first_word not in var_first.keys():
            var_first[first_word] = line_num, line
        var_last[first_word] = line_num, line
    concise_def_lines=[]
    for var in var_first.keys():
        concise_def_lines.append(var_first[var])
        if var_first[var] != var_last[var]:
            concise_def_lines.append(var_last[var])
    def_lines = sorted(concise_def_lines, key=lambda x: x[0])
    def_code = "".join([item[1] for item in def_lines])
    return def_code+buggy_line_code

def find_func(test_class_lines, trigger_func, line_number, whether_Exception = False, whether_multi_call_relations = False, layer = "external"):
    # get the test functions code lines
    start, end = 0, 0
    if not line_number == -1:
        for inx, lin in enumerate(test_class_lines):
            if trigger_func + '(' in lin.strip():
                if inx < line_number:
                    start = inx

    else:
        print("Now, line_number == -1")
        for inx, lin in enumerate(test_class_lines):
            if trigger_func + '(' in lin.strip():
                start = inx
                print("line_number == -1， finding func_name as same as trigger func name!")

    if start == 0:
        print("start == 0, not finding the start line number of trigger_func!")
        return None

    countl, countr = 0, 0
    for inx, lin in enumerate(test_class_lines[start:]):
        countl += lin.count("{")
        countr += lin.count("}")
        if countl == countr > 0:
            end = start + inx
            break

    # if line_number == -1, it means to extract the whole function's source code
    if line_number == -1:
        test_func_lines = test_class_lines[start - 1:end + 1]
        # return the whole function, including function name line
        return test_func_lines

    # check if line_number is correct, maybe the sentence hasn't finished at this line
    buggy_line_code = test_class_lines[line_number]
    # if the buggy line is like "fail()", just input the line before it
    if buggy_line_code.strip() == "fail();":
        buggy_line_code = test_class_lines[line_number - 1] + buggy_line_code

    original_line_number = line_number
    original_inx = original_line_number - start
    while not test_class_lines[line_number].strip().endswith(';') and \
            not test_class_lines[line_number].strip().endswith('{'):
        line_number += 1
        str_tmp = test_class_lines[line_number]
        buggy_line_code += str_tmp

    # if only single test func in tcbk
    if not whether_multi_call_relations:
        # judge if the function has parameters
        element = trigger_func + "()"
        function_snippet_returned = []
        if element in test_class_lines[start]: # func has no parameters
            # judge whether the error is Exception or Assert
            if whether_Exception == True:
                # return from the first line to (including)buggy line of the function
                test_func_lines = test_class_lines[start+1:line_number+1]
            else: # Assert Failed Error, str will be processed outside the method
                return None

        else: # func has parameters
            # return from the func name line to (including)buggy line of the function
            test_func_lines = test_class_lines[start:line_number+1]
        # after deciding start and end line to extract, filter the lines having "assert" related sentence
        for inx, line in enumerate(test_func_lines):
            if "assert" in line and inx >= 0 and inx < original_inx-1 and trigger_func not in line:
                continue
            function_snippet_returned.append(line)
        return function_snippet_returned

    # if there are multiple functions called
    else:
        element = trigger_func + "()"
        function_snippet_returned = []
        # if the function is at the external layer
        if layer == 'external':
            # if having paras, the way to process Exception or Assert is the same
            # if no paras, the way to process Exception or Assert is also the same

            # judge if the function has parameters
            if element in test_class_lines[start]:  # func has no parameters
                # return from the first line to (including)buggy line of the function
                test_func_lines = test_class_lines[start + 1:line_number + 1]

            else: # func has parameters
                # return from the func name line to (including)buggy line of the function
                test_func_lines = test_class_lines[start:line_number + 1]

        elif layer == 'middle':
            test_func_lines = test_class_lines[start:line_number + 1]
        else: # the inner layer of function call
            if whether_Exception == True:
                test_func_lines = test_class_lines[start:line_number + 1]
            else: # Assert Failed Error, and then judge if the func has paras
                if element in test_class_lines[start]:
                    return None
                else:
                    test_func_lines = test_class_lines[start:line_number + 1]
        # after deciding start and end line to extract, filter the lines having "assert" related sentence
        for inx, line in enumerate(test_func_lines):
            if "assert" in line and inx >= 0 and inx < original_inx-1 and trigger_func not in line:
                continue
            function_snippet_returned.append(line)
        return function_snippet_returned


def analyze_traceback_and_extract_code_snippets(test_classes_paths, failing_test, testfunc_inx_in_tcbk, line_to_locate_in_traceback, error_name):
    # if no test func in tcbk, just extract the source code of the whole test function
    whether_no_test_func_in_tcbk = False

    # if the name of test func not corresponds to that in tcbk, following the tcbk to extract
    whether_not_crspd_to_tcbk = False

    # if exception type error, the line may like "if(Error Element causes Exception){", not in assert sentence
    # don't need add "//" to the line, after returning, just break
    whether_break_after_returning = False

    # judge the error type, Exception or AssertFailed
    whether_Exception = False
    if "Exception" in error_name:
        whether_Exception = True

    # if no function call relation, just one testfunc to de extracted
    # if multiple called func, they should be continuous in lines of traceback
    whether_multi_call_func = False

    buggy_line_number_in_tstcls = -1
    class_name = ''
    if testfunc_inx_in_tcbk == 0 or line_to_locate_in_traceback == '':
        print("Not finding test class in traceback!", "testfunc_inx_in_tcbk is", testfunc_inx_in_tcbk)
        print("line_to_locate_in_traceback is", line_to_locate_in_traceback)
        # it means not finding any test class in traceback
        whether_no_test_func_in_tcbk = True
    else:
        buggy_line_number_in_tstcls = int(line_to_locate_in_traceback.split(':')[-1].strip(')'))
        class_name = line_to_locate_in_traceback.split('.')[-2].split('(')[-1]

    # create a dict to record info in tcbk
    # key: ClassName value:Tup(ClassPath, BuggyLineNumber)
    dic_record_tcbk = {}
    range_scope = len(failing_test) if whether_no_test_func_in_tcbk else testfunc_inx_in_tcbk + 1
    for inx in range(range_scope):
        if not failing_test[inx].strip().startswith('at'):
            continue
        info_in_current_line = failing_test[inx].strip().split(' ')[-1]
        if '.ant.' in info_in_current_line:
            continue
        split_by_left_parentheses = info_in_current_line.split('(')
        class_path = split_by_left_parentheses[0]
        class_name_and_line = split_by_left_parentheses[-1].strip(')')
        function_called = class_path.split('.')[-1]

        # judge whether a line has info about buggy line number
        judge_tmp = class_name_and_line.split(':')
        if len(judge_tmp) <= 1:
            print("No buggy line number in the line of tcbk!")
            print("The info of this line is:", info_in_current_line)
            continue

        current_class_name = judge_tmp[0]
        if function_called == "<init>":
            function_called = current_class_name.strip(".java")
        # if not finding a number
        try:
            buggy_line_number_in_class = int(judge_tmp[-1])
        except Exception as e:
            print(f"Not finding buggy line number in line {inx} of tcbk!")
            continue
        class_path_before_current_class_name = class_path.split('.')[0:-2]
        class_path = '/'.join(class_path_before_current_class_name)
        class_path = class_path + '/' + current_class_name
        possible_test_class_path = buggy_project_path + '/' + test_trigger_dirs[0] + '/' + class_path
        possible_buggy_class_path = buggy_project_path + '/' + buggy_classes_dirs[0] + '/' + class_path
        tmp_line_number = buggy_line_number_in_class
        buggy_line_code = ''

        if not wo_contextual_code:
            if os.path.exists(possible_buggy_class_path):
                with open(possible_buggy_class_path, 'r') as f:
                    class_lines = f.readlines()
                buggy_line_code = class_lines[tmp_line_number - 1]
                # if the buggy line is like "fail()", just input the line before it
                if buggy_line_code.strip() == "fail();":
                    buggy_line_code = class_lines[tmp_line_number - 2] + buggy_line_code

                while not class_lines[buggy_line_number_in_class - 1].strip().endswith(';') and \
                        not class_lines[buggy_line_number_in_class - 1].strip().endswith('{'):
                    buggy_line_number_in_class += 1
                    str_tmp = class_lines[buggy_line_number_in_class - 1]
                    buggy_line_code += str_tmp
                dic_record_tcbk[inx] = (possible_buggy_class_path, tmp_line_number, function_called, buggy_line_code)
                print("finding the source code of current line of info in tcbk, it's buggy class file")

        if os.path.exists(possible_test_class_path):
            with open(possible_test_class_path, 'r') as f:
                class_lines = f.readlines()
            buggy_line_code = class_lines[tmp_line_number - 1]
            # if the buggy line is like "fail()", just input the line before it
            if buggy_line_code.strip() == "fail();":
                buggy_line_code = class_lines[tmp_line_number - 2] + buggy_line_code

            while not class_lines[buggy_line_number_in_class - 1].strip().endswith(';') and \
                    not class_lines[buggy_line_number_in_class - 1].strip().endswith('{'):
                buggy_line_number_in_class += 1
                str_tmp = class_lines[buggy_line_number_in_class - 1]
                buggy_line_code += str_tmp
            dic_record_tcbk[inx] = (possible_test_class_path, tmp_line_number, function_called, buggy_line_code)
            print("finding the source code of current line of info in tcbk, it's test class file")

        else:
            print("Not finding the source code of current line of info in tcbk")
        print("The current ClassName is:", current_class_name)

    # after constructing the dict, see how many elements have been recorded
    element_number = len(dic_record_tcbk)
    if element_number >= 2:
        whether_multi_call_func = True
        print("finding multi call function!")
    if whether_no_test_func_in_tcbk and element_number >= 1:
        whether_not_crspd_to_tcbk = True
        print("test func in tcbk not corresponds to that in trigger test func!")

    if whether_no_test_func_in_tcbk and not whether_not_crspd_to_tcbk: # not finding any test class in traceback, extract the whole test function
        # need three vars to input as paras
        # 1. test_class_lines: the source codes of a target source file
        line_number = -1
        test_class_plus_func = failing_test[0].strip().split('.')[-1]
        test_class_name = test_class_plus_func.split("::")[0]
        test_func = test_class_plus_func.split("::")[-1]
        test_class_lines = []
        for path in test_classes_paths:
            if test_class_name in path:
                with open(path, 'r') as fff:
                    test_class_lines = fff.readlines()

        code_str_list = find_func(test_class_lines, test_func, line_number)
        str_returned = ''.join(code_str_list)
        return str_returned

    if whether_multi_call_func == False:
        if not element_number == 1:
            print("The number of element in dict should be 1!")
            exit()
        first_key = list(dic_record_tcbk.keys())[0]
        tup = dic_record_tcbk[first_key]
        file_path = tup[0]
        line_number = tup[1]
        test_func_name = tup[2]
        buggy_line_code = tup[3]

        with open(file_path, 'r') as ff:
            test_class_lines = ff.readlines()
        code_str_list = find_func(test_class_lines, test_func_name, line_number - 1, whether_Exception, whether_multi_call_func)
        if code_str_list is not None:
            str_returned = ''.join(code_str_list) + '\n\n'
        else:
            # if returned value is None，processed with RE
            var_def_line_dict = build_var_def_line_dict(test_class_lines, test_func_name, line_number)
            str_returned = complete_def_code(buggy_line_code, var_def_line_dict)

    else:
        str_returned = ''
        class_name_keys = list(dic_record_tcbk.keys())
        class_name_keys.reverse()
        for inx, key in enumerate(class_name_keys):
            tup = dic_record_tcbk[key]
            file_path = tup[0]
            line_number = tup[1]
            test_func_name = tup[2]
            buggy_line_code = tup[3]

            with open(file_path, 'r') as ff:
                test_class_lines = ff.readlines()

            if inx == 0:
                code_str_list = find_func(test_class_lines, test_func_name, line_number - 1, whether_Exception, whether_multi_call_func, layer = 'external')
                if code_str_list is None:
                    continue
                str_returned += ''.join(code_str_list) + '\n\n'
            elif 0 < inx < element_number-1:
                code_str_list = find_func(test_class_lines, test_func_name, line_number - 1, whether_Exception, whether_multi_call_func, layer='middle')
                if code_str_list is None:
                    continue
                str_returned += ''.join(code_str_list) + '\n\n'
            else: # the last layer
                code_str_list = find_func(test_class_lines, test_func_name, line_number - 1, whether_Exception, whether_multi_call_func, layer='inner')
                if code_str_list is not None:
                    str_returned += ''.join(code_str_list) + '\n\n'
                else: # if returned value is None，processed with RE
                    var_def_line_dict = build_var_def_line_dict(test_class_lines, test_func_name, line_number)
                    pass_line_code = complete_def_code(buggy_line_code, var_def_line_dict)
                    str_returned += pass_line_code + '\n\n'

    return str_returned

def classify_test_cases_by_running_on_buggy_funcs(test_classes_paths, trigger_class_and_funcs, trigger_classes):
    # Start processing and getting the source code of buggy functions
    # get all the test functions one by one in the test class
    # check whether the test cases in test function can pass the buggy functions
    # prefix = "params"
    # suffix = ".bin"
    FailingTestsExceptionList = []
    for test_class_path in test_classes_paths:
        print(f"In test class{test_class_path}")
        test_func_list = []
        trigger_func_list = []
        with open(test_class_path, 'r') as f:
            source_code4test_class = f.readlines()
        for line in source_code4test_class:
            # search the source code of test class, and get the test function one by one
            line_strip = line.strip()
            func_name = extract_function_name(line_strip)
            if func_name is not None and func_name.startswith('test'):
                test_func_list.append(func_name)

        # collect the test function in which error is triggerred
        class_name = test_class_path.split('/')[-1].split('.')[0]
        for each_trigger_class_and_func in trigger_class_and_funcs:
            if '.' + class_name in each_trigger_class_and_func:
                trigger_func = each_trigger_class_and_func.split('::')[-1]
                if not trigger_func in trigger_func_list:
                    trigger_func_list.append(trigger_func)

        # decide the dir before test class
        trigger_class_decided = ''
        for trigger_class in trigger_classes:
            if class_name in trigger_class:
                trigger_class_decided = trigger_class

        # run the test functions which fails to pass the buggy functions and store the input in 'bin' file
        dict_record = {}
        dict_record["BS"] = []
        dict_record["BF"] = []

        dict_record4Exception = {}
        dict_record4Exception['Type'] = "String"
        dict_record4Exception['AS'] = []
        dict_record4Exception['BS'] = []
        dict_record4Exception['BF'] = []

        print("run the test functions which fails to pass the buggy functions and store the input in 'bin' file!")
        for trigger_func in trigger_func_list:
            var_def_line_dict = {}
            # something wrong in Mockito project, must run compile command first,
            # if just run test, compilation error will occur
            cmd_compile = f'defects4j compile -w {buggy_project_path}'
            process_compile = subprocess.Popen(cmd_compile.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # compilation_fb = ""
            try:
                stdout, stderr = process_compile.communicate(timeout=60)
                # compilation_fb = stdout.decode("utf-8")
            except Exception as e:
                print("Compilation error!")
                print(e)

            # print(compilation_fb)
            # call the defects4j command
            cmd_test = f'defects4j test -w {buggy_project_path} -t {trigger_class_decided}::{trigger_func}'
            process = subprocess.Popen(cmd_test.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            feedback_result = ""
            try:
                stdout, stderr = process.communicate(timeout=100)
                feedback_result = stdout.decode("utf-8")
            except subprocess.TimeoutExpired:
                print("test function time out!")
                # if timeout, we think an error trigger
            process.kill()
            # stdout, stderr = process.communicate()
            # feedback_result = stdout.decode("utf-8")
            # process.kill()
            whether_collect_BS_AS = True
            while True:
                if feedback_result.startswith("Failing tests: 0"):
                    print(f"After modification, the trigger test function {trigger_class_decided}::{trigger_func} can pass the buggy function!")

                    break

                elif feedback_result.startswith("Failing tests: 1"):
                    print("When running test function, an error occurs, so I need to add '//' to the place.")
                    # read the traceback file
                    traceback_file_path = buggy_project_path + '/' + 'failing_tests'
                    with open(traceback_file_path, 'r') as ff:
                        traceback_lines = ff.readlines()

                    line_to_locate_in_traceback = ''
                    ExceptionOrAssertFail = traceback_lines[1].split(':')[0].split('.')[-1]

                    testfunc_inx_in_tcbk = None
                    for inx, line in enumerate(traceback_lines):
                        line_strip = line.strip()
                        for trigger_class in trigger_classes:
                            if trigger_class in line_strip:
                                line_to_locate_in_traceback = line_strip
                                testfunc_inx_in_tcbk = inx

                    # add by  6/19
                    # source_file_dir = buggy_project_path + '/' + buggy_classes_dirs[0]
                    # test_file_dir = buggy_project_path + '/' + test_trigger_dirs[0]
                    BfItemStr = analyze_traceback_and_extract_code_snippets(test_classes_paths, traceback_lines,
                                                                testfunc_inx_in_tcbk, line_to_locate_in_traceback, ExceptionOrAssertFail)

                    try:
                        line_number = int(line_to_locate_in_traceback.split(':')[-1].strip(')'))
                    except Exception as e:
                        print(e)
                        print("Construct the json manually!")
                        class_name = traceback_lines[0].strip()
                        tup = (class_name, BfItemStr, ExceptionOrAssertFail)
                        FailingTestsExceptionList.append(tup)
                        break

                    class_name = line_to_locate_in_traceback.split('.')[-2].split('(')[-1]
                    buggy_line_code = ""
                    for path in test_classes_paths:
                        if '/' + class_name in path:
                            with open(path, 'r') as fff:
                                test_class_lines = fff.readlines()
                                # var_def_line_dict = build_var_def_line_dict(test_class_lines, trigger_func, line_number)

                            buggy_line_code = test_class_lines[line_number - 1]
                            # if the buggy line is like "fail()", just input the line before it
                            if buggy_line_code.strip() == "fail();":
                                buggy_line_code = test_class_lines[line_number - 2] + buggy_line_code

                            test_class_lines[line_number - 1] = "//" + test_class_lines[line_number - 1]
                            while not test_class_lines[line_number-1].strip().endswith(';'):
                                line_number += 1
                                str_tmp = test_class_lines[line_number - 1]
                                buggy_line_code += str_tmp
                                test_class_lines[line_number - 1] = "//" + str_tmp
                            with open(path, 'w') as ffff:
                                ffff.writelines(test_class_lines)
                            # var_def_lines = find_var_def_lines(buggy_line_code, var_def_line_dict)
                            # buggy_line_code = extend_buggy_line_code(buggy_line_code, var_def_lines,test_class_lines)
                            break
                            # after changing test class file, remove all the .class files and compile again
                    class_files_dir = os.path.join(buggy_project_path, "target")
                    if not os.path.exists(class_files_dir):
                        class_files_dir = os.path.join(buggy_project_path, "build")
                    if os.path.exists(class_files_dir):
                        cmd_rm = f"rm -r {class_files_dir}"
                        os.system(cmd_rm)

                    # record traceback for each failing test case
                    # with a tuple, (Class_name, The content of buggy line, ExceptionOrAssertFail)
                    # buggy_line_code = complete_def_code(buggy_line_code, var_def_line_dict)
                    tup = (class_name, BfItemStr, ExceptionOrAssertFail)
                    FailingTestsExceptionList.append(tup)

                    cmd_compile = f'defects4j compile -w {buggy_project_path}'
                    process = subprocess.Popen(cmd_compile.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    process.communicate()
                    process.kill()

                    process = subprocess.Popen(cmd_test.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        stdout, stderr = process.communicate(timeout=90)
                        feedback_result = stdout.decode("utf-8")
                    except subprocess.TimeoutExpired:
                        print("test function time out!")
                    process.kill()

                else:
                    # This may be compilation error, and the test function wouldn't run,
                    # so no .bin file will be created.
                    print("a compilation error may occur because of modifying test function(add // on)")
                    print(feedback_result)
                    print("For this bug, you should extract the test cases manually!!")
                    whether_collect_BS_AS = False
                    break
                    # exit()

            # having finishing running the test func where there is no passing test case, create .json for assert error.
            for path in test_classes_paths:
                if not whether_collect_BS_AS:
                    break
                if '/' + class_name in path:
                    with open(path, 'r') as fff:
                        test_class_lines = fff.readlines()
                        #get the test functions code lines
                        start, end = 0, 0
                        for inx, lin in enumerate(test_class_lines):
                            if trigger_func in lin.strip():
                                start = inx
                                break
                        countl, countr = 0, 0
                        for inx, lin in enumerate(test_class_lines[start:]):
                            countl += lin.count("{")
                            countr += lin.count("}")
                            if countl == countr > 0:
                                end = start+inx
                                break
                        test_func_lines = test_class_lines[start:end+1]

                        for inx, line in enumerate(test_func_lines):
                            line_strip = line.strip()
                            if line_strip.startswith("assert") or line_strip.startswith("Assert"):
                                tmp = []
                                tmp_str = ""
                                tmp_str += line_strip
                                tmp_line = inx
                                while not test_func_lines[tmp_line].strip().endswith(';'):
                                    tmp_line += 1
                                    tmp_str += test_func_lines[tmp_line].strip()
                                line_number = start + inx + 1
                                var_def_line_dict = build_var_def_line_dict(test_class_lines, trigger_func, line_number)
                                pass_line_code = complete_def_code(tmp_str, var_def_line_dict)
                                # print(pass_line_code)
                                tmp.append(pass_line_code)
                                dict_record["BS"].append(tmp)
                                dict_record4Exception["AS"].append(tmp)

                    break
    for tup in FailingTestsExceptionList:
        tmp = []
        tmp.append(tup[1])
        if "Exception" not in tup[2]:
            dict_record["BF"].append(tmp)

        else:
            dict_record4Exception["BF"].append(tmp)

    if len(dict_record["BF"]) > 0:
        json_string = json.dumps(dict_record)
        with open(f'/tmp/jsons/{prlist[0]}-{ids[0]}_Assert.json', 'w') as f:
            f.write(json_string)

    if len(dict_record4Exception["BF"]) > 0:
        json_string = json.dumps(dict_record4Exception)
        with open(f'/tmp/jsons/{prlist[0]}-{ids[0]}.json', 'w') as f:
            f.write(json_string)

    for tup in FailingTestsExceptionList:
        print(tup)
    # exit()
    return FailingTestsExceptionList

create_buggy_projects(buggy_project_path)

buggy_classes = find_buggy_classes(buggy_project_path)
buggy_classes_dirs = find_buggy_dir4buggy_classes(buggy_project_path)
modified_class_paths = construct_file_complete_path(buggy_project_path, buggy_classes_dirs, buggy_classes)

test_trigger_class_and_funcs = find_trigger_path(buggy_project_path)
test_trigger_dirs = find_dir4test_class(buggy_project_path)
if len(buggy_classes_dirs) > 1 or len(test_trigger_dirs) > 1:
    print("The number of source file(test file) dir is more than 1!")
    exit()

test_trigger_class = []
for test_trigger_class_and_func in test_trigger_class_and_funcs:
    if test_trigger_class_and_func.split('::')[0] not in test_trigger_class:
        test_trigger_class.append(test_trigger_class_and_func.split('::')[0])

test_class_paths = construct_file_complete_path(buggy_project_path, test_trigger_dirs, test_trigger_class)

# after modifying the source code of buggy class, use test class to classify the test cases,
# which test cases can pass the buggy functions and which can't.
FailingTestsExceptionList = classify_test_cases_by_running_on_buggy_funcs(test_class_paths, test_trigger_class_and_funcs, test_trigger_class)
subprocess.run('rm -rf ' + buggy_project_path, shell=True)


