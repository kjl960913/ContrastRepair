import json
import sys

import javaobj
import os
import re

# path_obj_for_lang_12 = "/Users/Desktop/seed_20230503120539000332/"
# /workspace/experiments/ContrastR/Lang-12/BF/seed_20230515082039000773  an example dir
# from loguru import logger

path = '/workspace/experiments/ContrastR'
json_dir = '/tmp/'
level = "DEBUG"
# logger.configure(handlers=[{"sink": sys.stderr, "level": level}]) # TODO: fix file output
log_file = os.path.join('/workspace/experiments/ContrastR', 'generate_json4Exception.log')
# if os.path.exists(log_file):
#     os.remove(log_file)
# logger.add(log_file, level=level)

def convert_java_obj_to_str(obj):
    # Check the type of the object
    if isinstance(obj, javaobj.JavaObject):
        # Check if it's a primitive type
        type = obj.classdesc.name
        if type in ['java.lang.Integer', 'java.lang.Double', 'java.lang.Float', 'java.lang.Long', 'java.lang.Short',
                       'java.lang.Byte', 'java.lang.Character', 'java.lang.Boolean']:
            # Convert the value to a string
            value = str(obj.value)
            print("Primitive type value:", value)
        else:
            value = str(obj)
            print("Object type:", type)
            print(value)
        return value
    elif isinstance(obj, javaobj.JavaArray):
        # Check if it's an array
        element_type = obj.element_type
        if element_type in ['java.lang.Integer', 'java.lang.Double', 'java.lang.Float', 'java.lang.Long',
                            'java.lang.Short', 'java.lang.Byte', 'java.lang.Character', 'java.lang.Boolean']:
            # Convert array elements to strings and combine them
            print("Array of primitive types:")
        else:
            print("Array of objects")
        values = [str(element) for element in obj]
        array_str = ", ".join(values)
        print(array_str)
        return array_str
    else:
        print("Unknown object type")
        value = str(obj)
        return value


def process_mutation_dir(mutation_path):
    print(f"mutation path is:{mutation_path}")
    test_case_str = ""
    element_list = []
    files_in_dir = [f for f in os.listdir(mutation_path) if
                       os.path.isfile(os.path.join(mutation_path, f))]
    if len(files_in_dir) == 0:
        print(f"The current mutation dir {mutation_path} has no element")
        return

    pattern = re.compile(r'(\d+)\.obj')
    files_replaced_obj = [f for f in files_in_dir if pattern.match(f)]
    files_replaced_obj.sort(key=lambda f: int(pattern.search(f).group(1)))
    if len(files_replaced_obj) == 0:
        print(f"The current mutation dir {mutation_path} has no .obj file")
        return
    for f in files_replaced_obj:
        print(f)
    print("for each all .obj, then print their value")
    for inx, obj_file in enumerate(files_replaced_obj):
        number = pattern.search(obj_file).group(1)
        # subtract means the number of .obj file which haven't been saved
        subtract = int(number) - inx
        if subtract > 0:
            for i in range(subtract):
                element_list.append('...')

        with open(mutation_path + '/' + obj_file, "rb") as fd:
            jobj = fd.read()
        try:
            pobj = javaobj.loads(jobj)
            # value = pobj.value
            # print("Value:", value)
            value = convert_java_obj_to_str(pobj)
            print("Value:", value)
        except Exception as e:
            print(e)
            element_list.append('...')
            continue
        # element_list.append(str(pobj))
        print(pobj)
        element_list.append(str(value))
    test_case_str = ", ".join(element_list)
    print(test_case_str)
    return test_case_str

# process_mutation_dir(path_obj_for_lang_12)

def process_testcase_to_json(path):

    # get all the bug-projects in path
    bug_projects = os.listdir(path)
    bug_projects = [bug_pj for bug_pj in bug_projects if "-" in bug_pj]
    print("bug projects are:")
    print(bug_projects)
    for dir in bug_projects:
        path_json_set = "/tmp/jsons/exception"
        jsons_set = os.listdir(path_json_set)
        jsons_set = [element.split('.')[0] for element in jsons_set]

        if dir in jsons_set:
            continue
        # if dir == "Time-7":
        #     continue
        # if not dir == "Lang-12":
        #     continue

        json_dict = {}
        json_dict['BF'] = []
        json_dict['BS'] = []
        json_dict['AS'] = []
        json_dict['Type'] = ['String']

        project_dir = os.path.join(path, dir)
        if os.path.isdir(project_dir) and "-" in dir:
            path_BF = os.path.join(project_dir, 'BF')
            path_BS = os.path.join(project_dir, 'BS')
            path_AS = os.path.join(project_dir, 'AS')

            BF_cases_dirs = os.listdir(path_BF)
            BF_cases_dirs = [bfdir for bfdir in BF_cases_dirs if "seed" in bfdir]
            if len(BF_cases_dirs) == 0:
                continue
            for testcase in BF_cases_dirs:
                testcase_dir = os.path.join(path_BF, testcase)
                case_str = process_mutation_dir(testcase_dir)
                temp = []
                temp.append(case_str)
                json_dict['BF'].append(temp)

            if os.path.exists(path_BS):
                BS_cases_dirs = os.listdir(path_BS)
                BS_cases_dirs = [bsdir for bsdir in BS_cases_dirs if "seed" in bsdir]
                print("BS_cases_dirs are:")
                print(BS_cases_dirs)
                for testcase in BS_cases_dirs:
                    testcase_dir = os.path.join(path_BS, testcase)
                    case_str = process_mutation_dir(testcase_dir)
                    temp = []
                    temp.append(case_str)
                    json_dict['BS'].append(temp)

            if os.path.exists(path_AS):
                AS_cases_dirs = os.listdir(path_AS)
                AS_cases_dirs = [asdir for asdir in AS_cases_dirs if "mutation_" in asdir]
                print("path_AS is:")
                print(path_AS)
                print("AS_cases_dirs are:")
                print(AS_cases_dirs)
                for testcase in AS_cases_dirs:
                    testcase_dir = os.path.join(path_AS, testcase)
                    case_str = process_mutation_dir(testcase_dir)
                    temp = []
                    temp.append(case_str)
                    json_dict['AS'].append(temp)

        if len(json_dict['BF']) == 0 and len(BF_cases_dirs) > 0:
            print(f'{project_dir} has exception, but no type to mutate, process to get json manually!')
            # logger.debug(f'{project_dir} has exception, but no type to mutate, process to get json manually!')
            continue
        json_str = json.dumps(json_dict)
        json_path = f"/tmp/jsons/exception/{dir}.json"
        with open(json_path, 'w') as f:
            f.write(json_str)
        # logger.info(f"generate {json_path}!")

def main():
    process_testcase_to_json(path)

if __name__ == "__main__":
    main()
