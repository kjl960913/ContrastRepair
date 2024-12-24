import os
import re
import json
import time
import signal
import javalang
import subprocess

from loguru import logger
from config import Config

os.environ['PATH'] += ':/root/defects4j/framework/bin'
java_home_path = "/root/jdk1.8.0_371"
os.environ["JAVA_HOME"] = java_home_path
REAL_SOURCE = []

# error_str = ['CompileError', 'SyntaxError', 'TimeOutError']
class Validation:

    def __init__(self):
        self._config = Config.get_instance()

    @staticmethod
    def _run_d4j_test(source, testmethods, bug_id, project, bug):
        bugg = False
        compile_fail = False
        timed_out = False
        entire_bugg = False
        error_string = ""

        try:
            tokens = javalang.tokenizer.tokenize(source)
            parser = javalang.parser.Parser(tokens)
            parser.parse()
        except:
            print("Syntax Error")
            return compile_fail, timed_out, bugg, entire_bugg, True, "SyntaxError"

        for t in testmethods:
            cmd = 'defects4j test -w %s/ -t %s' % (('/tmpConR/' + bug_id), t.strip())
            Returncode = ""
            error_file = open("stderr.txt", "wb")
            child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=error_file, bufsize=-1,
                                     start_new_session=True)
            while_begin = time.time()
            while True:
                Flag = child.poll()
                if Flag == 0:
                    Returncode = child.stdout.readlines()  # child.stdout.read()
                    print(b"".join(Returncode).decode('utf-8'))
                    error_file.close()
                    break
                elif Flag != 0 and Flag is not None:
                    compile_fail = True
                    error_file.close()
                    with open("stderr.txt", "rb") as f:
                        r = f.readlines()
                    for index, line in enumerate(r):
                        if re.search(':\serror:\s', line.decode('utf-8')):
                            error_string = line.decode('utf-8').strip()
                            if "cannot find symbol" in error_string:
                                error_string += " (" + r[index + 3].decode('utf-8').split("symbol:")[-1].strip() + ")"
                            break
                    print("Error")
                    print(error_string)
                    if error_string == "":
                        subprocess.run('rm -rf ' + '/tmpConR/' + bug_id, shell=True)
                        subprocess.run(
                            "defects4j checkout -p %s -v %s -w %s" % (project, bug + 'b', ('/tmpConR/' + bug_id)),
                            shell=True)

                    break
                elif time.time() - while_begin > 15:
                    error_file.close()
                    os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                    timed_out = True
                    error_string = "TimeOutError"
                    break
                else:
                    time.sleep(0.001)
            log = Returncode
            if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
                continue
            else:
                bugg = True
                break

        # Then we check if it passes all the tests, include the previously okay tests
        if not bugg:
            print('So you pass the basic tests, Check if it passes all the test, include the previously passing tests')
            cmd = 'defects4j test -w %s/' % ('/tmpConR/' + bug_id)
            Returncode = ""
            child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1,
                                     start_new_session=True)
            while_begin = time.time()
            while True:
                Flag = child.poll()
                if Flag == 0:
                    Returncode = child.stdout.readlines()  # child.stdout.read()
                    break
                elif Flag != 0 and Flag is not None:
                    bugg = True
                    break
                elif time.time() - while_begin > 180:
                    os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                    bugg = True
                    error_string = "TimeOutError"
                    break
                else:
                    time.sleep(0.01)
            log = Returncode
            if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
                print('success')
            else:
                entire_bugg = True

        return compile_fail, timed_out, bugg, entire_bugg, False, error_string

    @staticmethod
    def _grab_failing_testcode(bug_id, file_name, test_method_name, line_number, tmp_bug_id):
        test_dir = os.popen("defects4j export -p dir.src.tests -w /tmpConR/" + tmp_bug_id).readlines()[-1].strip()

        if not os.path.isfile("/tmpConR/" + tmp_bug_id + "/" + test_dir + "/" + file_name + ".java"):
            return "", ""
        try:
            with open("/tmpConR/" + tmp_bug_id + "/" + test_dir + "/" + file_name + ".java", "r") as f:
                source = f.read()
        except:
            with open("/tmpConR/" + tmp_bug_id + "/" + test_dir + "/" + file_name + ".java", "r",
                      encoding='ISO-8859-1') as f:
                source = f.read()
        # print(source)
        # method_dict = parse_source(source)
        lines = source.splitlines()

        if line_number == "":
            return None, ""
            # return "\n".join(lines[method_dict[test_method_name]['start'] - 1:method_dict[test_method_name]['end']]), ""
        else:
            return None, lines[int(line_number) - 1]
            # return "\n".join(lines[method_dict[test_method_name]['start'] - 1:method_dict[test_method_name]['end']]), lines[int(line_number) - 1]

    # process patches generated in QuixBugs

    def _write_file4quix(self, folder, patch, file_name, bug, lang="java"):
        with open(os.path.join(folder, file_name), "w") as f:
            f.write(patch)
        valid, message = self._validate_one_patch4quix(patch, bug, dataset_name=lang)
        return valid, message


    def _validate_one_patch4quix(self, patch, bug_id, dataset_name="java"):
        global REAL_SOURCE
        current_path = os.getcwd()
        if dataset_name == "java":
            with open(os.path.join(current_path, "QuixBugs/fault_location/QuixBugs_Java_info.json"), "r") as f:
                bug_dict = json.load(f)
            key = bug_id
            start = bug_dict[key]['start']
            end = bug_dict[key]['end']
            val_dir_path = '/root/tmpQuixBugs/java_programs/'
            ori_dir_path = os.path.join(current_path, 'QuixBugs/java_programs')
            py_file_name = bug_id + '.java'
            val_bg_func_path = val_dir_path + py_file_name
            ori_bg_func_path = ori_dir_path + '/' + py_file_name
            # if os.path.exists(val_bg_func_path):
            subprocess.run('rm ' + val_bg_func_path, shell=True)
            subprocess.run('cp ' + ori_bg_func_path + ' ' + val_bg_func_path, shell=True)
            new_bg_file_str = ''
            with open(val_bg_func_path, 'r') as f:
                ori_bf_code_list = f.readlines()
            new_bg_file_str = "".join(ori_bf_code_list[:start - 1]) + patch + "".join(ori_bf_code_list[end:])
            # new_bg_file_str = patch
            with open(val_bg_func_path, 'w') as f:
                f.write(new_bg_file_str)

            cmd = 'cd /root/tmpQuixBugs && /root/.sdkman/candidates/gradle/current/bin/gradle test --tests %s' % (bug_id + '_TEST')
            child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, bufsize=-1,
                                     start_new_session=True)
            stdout, stderr = child.communicate(timeout=100)
            Returninfo = []
            if stdout is not None:
                feedback_result_out = stdout.decode("utf-8")

            feedback_lines = feedback_result_out.split('\n')

            # replace current patch file in case of compilation error for later bug patch
            subprocess.run('cp ' + ori_bg_func_path + ' ' + val_bg_func_path, shell=True)

            for inx, fdbk_line in enumerate(feedback_lines):
                line_stp = fdbk_line.strip()
                start = 0
                if "BUILD SUCCESSFUL" in line_stp:
                    return True, None
                if "Task :compileJava FAILED" in line_stp:
                    return False, feedback_result_out
                if "Task :test FAILED" in line_stp:
                    start = inx
                    return False, "".join(feedback_lines[start:])
        else:
            with open(os.path.join(current_path, 'QuixBugs/fault_location/QuixBugs_Python_info.json'), "r") as f:
                bug_dict = json.load(f)
            key = bug_id + '.py'
            start = bug_dict[bug_id]['start']
            end = bug_dict[bug_id]['end']
            val_dir_path = '/root/tmpQuixBugs/python_programs/'
            ori_dir_path = os.path.join(current_path, 'QuixBugs/python_programs')
            py_file_name = key
            val_bg_func_path = val_dir_path + py_file_name
            ori_bg_func_path = ori_dir_path + '/' + py_file_name
            # if os.path.exists(val_bg_func_path):
            subprocess.run('rm ' + val_bg_func_path, shell=True)
            subprocess.run('cp ' + ori_bg_func_path + ' ' + val_bg_func_path, shell=True)
            new_bg_file_str = ''
            with open(val_bg_func_path, 'r') as f:
                ori_bf_code_list = f.readlines()
            new_bg_file_str = "".join(ori_bf_code_list[:start-1]) + patch + "".join(ori_bf_code_list[end:])
            with open(val_bg_func_path, 'w') as f:
                f.write(new_bg_file_str)

            cmd = 'cd /root/tmpQuixBugs && /opt/conda/envs/chatgpt/bin/pytest --timeout=300 --runslow /root/tmpQuixBugs/python_testcases/%s' % ('test_' + key)
            # cmd = 'cd %s && pytest --timeout=20 python_testcases/%s' % ("/root/QuixBugs", key)
            Returninfo = []
            child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, bufsize=-1,
                                     start_new_session=True)
            stdout, stderr = child.communicate(timeout=100)
            if stdout is not None:
                feedback_result_out = stdout.decode("utf-8")
            feedback_lines = feedback_result_out.split('\n')
            final_line = feedback_lines[-2]
            child.kill()

            # replace current patch file in case of compilation error for later bug patch
            subprocess.run('cp ' + ori_bg_func_path + ' ' + val_bg_func_path, shell=True)

            if not " failed, " in final_line and " passed" in final_line:
                return True, None
            else:
                for line in feedback_lines:
                    lstp = line.strip()
                    if "Error" in lstp:
                        Returninfo.append(lstp)
                Returninfo_str = "\n".join(Returninfo)
                return False, Returninfo_str


    def _validate_one_patch(self, folder, patch, bug_id, dataset_name="defects4j_1.2_full", tmp_prefix="test", reset=False):
        global REAL_SOURCE

        if dataset_name == "defects4j_1.2_full":
            with open(os.path.join(folder, "single_function_repair.json"), "r") as f:
                bug_dict = json.load(f)

        bug, project = bug_id.split("-")[1], bug_id.split("-")[0]
        start = bug_dict[bug_id]['start']
        end = bug_dict[bug_id]['end']
        with open(os.path.join(folder, "location/{}.buggy.lines".format(bug_id)), "r") as f:
            locs = f.read()
        loc = set([x.split("#")[0] for x in locs.splitlines()])  # should only be one
        loc = loc.pop()
        tmp_bug_id = tmp_prefix + project + bug

        if reset:  # check out project again
            subprocess.run('rm -rf ' + '/tmpConR/' + tmp_prefix + "*", shell=True)  # clean up
            subprocess.run('rm -rf ' + '/tmpConR/' + tmp_bug_id, shell=True)
            subprocess.run("defects4j checkout -p %s -v %s -w %s" % (project, bug + 'b', ('/tmpConR/' + tmp_bug_id)),
                           shell=True)
            # add by kjkl 6/16
            # Some unknown errors in Project Mockito, such as Mockito-12 24
            # If just run command "defects4j test", compilation error occurs
            # So run the command "defects4j compile" first, will get rid of this
            if project == "Mockito":
                subprocess.run("defects4j compile -w %s" % ('/tmpConR/' + tmp_bug_id), shell=True)

        testmethods = os.popen('defects4j export -w %s -p tests.trigger' % ('/tmpConR/' + tmp_bug_id)).readlines()
        source_dir = os.popen("defects4j export -p dir.src.classes -w /tmpConR/" + tmp_bug_id).readlines()[-1].strip()

        if reset:
            try:
                with open("/tmpConR/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'r') as f:
                    REAL_SOURCE = f.read().splitlines()
            except:
                with open("/tmpConR/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'r', encoding='ISO-8859-1') as f:
                    REAL_SOURCE = f.read().splitlines()

        source = REAL_SOURCE
        source = "\n".join(source[:start - 1] + patch.splitlines() + source[end:])

        try:
            with open("/tmpConR/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'w') as f:
                f.write(source)
            subprocess.run("touch -d '12 December' " + "/tmpConR/" + tmp_bug_id + "/" + source_dir + "/" + loc,
                           shell=True)
        except:
            with open("/tmpConR/" + tmp_bug_id + "/" + source_dir + "/" + loc, 'w', encoding='ISO-8859-1') as f:
                f.write(source)
            subprocess.run("touch -d '12 December' " + "/tmpConR/" + tmp_bug_id + "/" + source_dir + "/" + loc,
                           shell=True)

        compile_fail, timed_out, bugg, entire_bugg, syntax_error, error_string = self._run_d4j_test(source,
                                                                                                    testmethods,
                                                                                                    tmp_bug_id,
                                                                                                    project, bug)
        line_number = ""
        if not compile_fail and not timed_out and not bugg and not entire_bugg and not syntax_error:
            print("{} has valid patch".format(bug_id))
            return True, ("valid", "", "")
        else:
            test_method_name, failing_line = "", ""
            if (bugg or entire_bugg) and not compile_fail:
                if not os.path.isfile('/tmpConR/' + tmp_bug_id + '/failing_tests'):
                    error_string = "CompileError"
                else:
                    try:
                        with open('/tmpConR/' + tmp_bug_id + '/failing_tests', "r") as f:
                            text = f.read()
                    except:
                        with open('/tmpConR/' + tmp_bug_id + '/failing_tests', "r", encoding='ISO-8859-1') as f:
                            text = f.read()
                    if len(text.split("--- ")) >= 2:
                        # error_string = text[1]
                        x = text.split("--- ")[1]  # just grab first one
                        test_name = x.splitlines()[0]
                        file_name = test_name.split("::")[0].replace(".", "/")
                        if len(test_name.split("::")) == 1:
                            error_string = ""
                        else:
                            test_method_name = test_name.split("::")[1]
                            line_number = ""
                            error_string = x.splitlines()[1]
                            for line in x.splitlines()[1:]:
                                if test_method_name in line:
                                    line_number = line.split(":")[-1].split(")")[0]
                                    file_name = line.split("." + test_method_name)[0].split("at ")[1].replace(".", "/")
                                    break
                            logger.info("Print Log:", file_name, test_method_name, line_number)
                            failing_function, failing_line = self._grab_failing_testcode(bug_id.split(".java")[0], file_name, test_method_name, line_number, tmp_bug_id)
                    else:
                        error_string = ""
            print("{} has invalid patch".format(bug_id))
            return False, (error_string, test_method_name, failing_line, line_number)

    def write_file(self, folder, patch, file_name, bug, skip_val=True, lang="java", reset=False):
        # print(args)
        # logger.debug('folder: {}', folder)
        # logger.debug('patch: {}', patch)
        # logger.debug('file_name: {}', file_name)
        # logger.debug('bug: {}', bug)

        with open(os.path.join(folder, file_name), "w") as f:
            f.write(patch)

        if skip_val:
            return False, "Not Evaluated"

        message = "Not needed"
        # @ todo: only support java
        valid, message = self._validate_one_patch(folder=self._config.dataset_folder, patch=patch, bug_id=bug, reset=reset, tmp_prefix=self._config.tmp_prefix)
        return valid, message

    @staticmethod
    def preprocess_run_all_test(d4j_folder):
        cmd = 'defects4j test -w %s/' % d4j_folder
        Returncode = ""
        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1,
                                 start_new_session=True)
        while_begin = time.time()
        timed_out = False
        bugg = False
        while True:
            Flag = child.poll()
            if Flag == 0:
                Returncode = child.stdout.readlines()  # child.stdout.read()
                break
            elif Flag != 0 and Flag is not None:
                bugg = True
                break
            elif time.time() - while_begin > 180:
                os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                bugg = True
                timed_out = True
                break
            else:
                time.sleep(1)
        log = Returncode
        # logger.info(log)
        entire_bugg = False
        if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
            # logger.info('success')
            # endtime = time.time()
            pass
        else:
            entire_bugg = True

        logger.info('===> results"')
        if timed_out:
            logger.info("Timed Out")
            return 2
        elif bugg:
            logger.info("Failed Testcase")
            return 1
        elif entire_bugg:
            logger.info("Failed Original Testcase")
            return 1
        else:
            logger.info("Success (Plausible Patch)")
            return 0

    @staticmethod
    def preprocess_run_specific_test(d4j_folder, command):
        cmd = 'defects4j test -w %s/ -t %s' % (d4j_folder, command)
        Returncode = ""
        child = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=-1,
                                 start_new_session=True)
        while_begin = time.time()
        timed_out = False
        bugg = False
        while True:
            Flag = child.poll()
            if Flag == 0:
                Returncode = child.stdout.readlines()  # child.stdout.read()
                break
            elif Flag != 0 and Flag is not None:
                bugg = True
                break
            elif time.time() - while_begin > 60:
                os.killpg(os.getpgid(child.pid), signal.SIGTERM)
                bugg = True
                timed_out = True
                break
            else:
                time.sleep(1)
        log = Returncode
        # logger.info(log)
        entire_bugg = False
        if len(log) > 0 and log[-1].decode('utf-8') == "Failing tests: 0\n":
            # logger.info('success')
            # endtime = time.time()
            pass
        else:
            entire_bugg = True

        logger.info('===> results"')
        if timed_out:
            logger.info("Timed Out")
            return 2
        elif bugg:
            logger.info("Failed Testcase")
            return 1
        elif entire_bugg:
            logger.info("Failed Original Testcase")
            return 1
        else:
            logger.info("Success (Plausible Patch)")
            return 0
