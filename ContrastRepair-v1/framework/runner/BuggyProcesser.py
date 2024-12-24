import glob
import json
import os
import shutil
import subprocess

from dataclasses import asdict
from loguru import logger

from framework.data.BuggyRecord import BuggyRecord
from framework.runner.Validation import Validation

os.environ['PATH'] += ':/root/defects4j/framework/bin'
java_home_path = "/root/jdk1.8.0_371"
os.environ["JAVA_HOME"] = java_home_path
class BuggyProcessor:

    INITIAL_JSON = 'buggy_record_initial.json'
    MUTATION_JSON = 'buggy_record_mutation.json'
    VERIFY_JSON = 'buggy_record_verify.json'

    def __init__(self, save_folder:str, java_tool: str):

        self._save_folder = save_folder
        if not os.path.exists(save_folder):
            os.makedirs(save_folder)

        self._java_tool = java_tool
        self._bug_record = BuggyRecord()

    def _jar_mask_test_case(self, d4j_folder: str, br: BuggyRecord):
        cmd = f"java -jar {self._java_tool} " \
              f"mark " \
              f"{os.path.join(d4j_folder, br.test_case_file_path)} " \
              f"{br.test_case_error_line} " \
              f"{os.path.join(d4j_folder, br.buggy_func_package)} " \
              f"{os.path.join(d4j_folder, br.test_case_package)} " \
              f"{os.path.join(d4j_folder, br.lib_package)}"

        logger.info(cmd)
        pmark = subprocess.Popen(cmd, shell=True)
        pmark.wait()

    def _jar_obtain_method_hash(self, d4j_folder: str, br: BuggyRecord):
        logger.info('--> Instrument for buggy func.')
        cmd = f"java -jar {self._java_tool} " \
              f"hash " \
              f"{os.path.join(d4j_folder, br.buggy_func_file_path)} " \
              f"{br.buggy_func_method_name} " \
              f"{br.buggy_func_start_line} " \
              f"{br.buggy_func_end_line} " \
              f"{br.tmp_folder} " \
              f"{os.path.join(d4j_folder, br.buggy_func_package)} " \
              f"{os.path.join(d4j_folder, br.test_case_package)} " \
              f"{os.path.join(d4j_folder, br.lib_package)}"
        logger.info(cmd)
        phash = subprocess.Popen(cmd, shell=True)
        phash.wait()

    def _jar_instrument_write_before(self, d4j_folder: str, br: BuggyRecord):
        cmd = f"java -jar {self._java_tool} " \
              f"initial " \
              f"{os.path.join(d4j_folder, br.buggy_func_file_path)} " \
              f"{br.buggy_func_method_name} " \
              f"{br.hash} " \
              f"{br.tmp_folder} " \
              f"{os.path.join(d4j_folder, br.buggy_func_package)} " \
              f"{os.path.join(d4j_folder, br.test_case_package)} " \
              f"{os.path.join(d4j_folder, br.lib_package)}"
        logger.info(cmd)
        pin = subprocess.Popen(cmd, shell=True)
        pin.wait()

    def _jar_instrument_verify(self, d4j_folder: str, br: BuggyRecord):
        cmd = f"java -jar {self._java_tool} " \
              f"verify " \
              f"{os.path.join(d4j_folder, br.buggy_func_file_path)} " \
              f"{br.buggy_func_method_name} " \
              f"{br.hash} " \
              f"{br.verify_command_file} " \
              f"{os.path.join(d4j_folder, br.buggy_func_package)} " \
              f"{os.path.join(d4j_folder, br.test_case_package)} " \
              f"{os.path.join(d4j_folder, br.lib_package)}"
        logger.info(cmd)
        pin = subprocess.Popen(cmd, shell=True)
        pin.wait()

    @staticmethod
    def _d4j_checkout(d4j_folder, bug_id):
        cmd = "defects4j checkout -p %s -v %s -w %s" % (bug_id.split('-')[0], bug_id.split('-')[1] + 'b', d4j_folder)
        logger.info(cmd)
        pcheck = subprocess.Popen(cmd, shell=True)
        pcheck.wait()
        logger.info('Generate checkout for {}', bug_id)

    @staticmethod
    def _d4j_compile(d4j_folder, bug_id):
        logger.info("--> Compile d4j.")
        cmd = "defects4j compile -w %s" % d4j_folder
        logger.info(cmd)
        pcheck = subprocess.Popen(cmd, shell=True)
        pcheck.wait()
        logger.info('Compile buggy for {}', bug_id)

    @staticmethod
    def _d4j_triggers(d4j_folder, bug_id):
        trigger_commands = []
        logger.info("--> Extract d4j triggers.")
        cmd = "defects4j export -p tests.trigger -w %s" % d4j_folder
        logger.info(cmd)
        trigger_lines = os.popen(cmd).readlines()
        logger.debug(trigger_lines)
        for tl in trigger_lines:
            if "::" in tl:
                trigger_commands.append(tl.rstrip())
        logger.info('Extract triggers for {}: {}', bug_id, trigger_commands)
        return trigger_commands

    @staticmethod
    def _d4j_buggy_func(d4j_folder):
        cmd = "defects4j export -p classes.modified -w %s" % d4j_folder
        logger.info(cmd)
        buggy_file_point = os.popen(cmd).readlines()[-1]
        cmd = "defects4j export -p dir.bin.classes -w %s" % d4j_folder
        buggy_package_path = os.popen(cmd)
        buggy_package_path = buggy_package_path.readlines()
        buggy_package_path = buggy_package_path[-1]
        buggy_file_path = '/'.join(buggy_file_point.split('.'))
        buggy_file_path = os.path.join(buggy_package_path, buggy_file_path + '.class')
        return buggy_package_path, buggy_file_path

    @staticmethod
    def _d4j_test_case(d4j_folder, command):
        cmd = "defects4j export -p dir.bin.tests -w %s" % d4j_folder
        logger.info(cmd)
        test_case_package_path = os.popen(cmd).readlines()[-1]
        test_case_file_path = '/'.join(command.split('::')[0].split('.'))
        test_case_file_path = os.path.join(test_case_package_path, test_case_file_path + '.class')
        return test_case_package_path, test_case_file_path, command.split('::')[1]

    @staticmethod
    def _d4j_lib_folder(d4j_folder):
        cmd = "defects4j export -p dir.bin.tests -w %s" % d4j_folder
        logger.info(cmd)
        test_case_package_path = os.popen(cmd).readlines()[-1]
        class_parent_dir = os.path.dirname(os.path.join(d4j_folder, test_case_package_path))
        other_libs_name = os.listdir(class_parent_dir)
        lib_package = test_case_package_path
        if len(other_libs_name) > 2:
            for item in other_libs_name:
                item_path = '/'.join(test_case_package_path.split('/')[:-1])  # os.path.join(class_parent_dir, item)
                item_path = os.path.join(item_path, item)  # item_path.split('d4j_initial/')[1]
                if 'lib' in item_path:
                    lib_package = item_path
                    break
        return lib_package

    @staticmethod
    def _parse_test_case_error_line_from_failing_log(d4j_folder: str, br: BuggyRecord):
        fail_file = os.path.join(d4j_folder, 'failing_tests')
        if not os.path.exists(fail_file):
            return None

        try:
            with open(fail_file, "r") as f:
                text = f.read()
        except:
            with open(fail_file, "r", encoding='ISO-8859-1') as f:
                text = f.read()
        # logger.debug(text)
        line_number = None
        if len(text.split("--- ")) >= 2:
            x = text.split("--- ")[1]
            command = x.splitlines()[0].rstrip()
            logger.debug(command)
            logger.debug(br.command)
            if command not in br.command:
                return None

            if 'Exception' in x.splitlines()[1]:
                error_type = 'Exception'
            else:
                error_type = 'Assertion'

            br.type = error_type
            if len(command.split("::")) > 1:
                test_func_name = br.command.split("::")[1]
                test_file_name = br.command.split("::")[0]
                for line in x.splitlines()[2:]:
                    tmp_method_name = line.split("(")[0].split(".")[-1]
                    if test_func_name == tmp_method_name:
                        if ":" in line:
                            line_number = line.split(":")[1].split(")")[0]

                if line_number is None:
                    # todo: parse other files
                    for line in x.splitlines()[1:]:
                        if '<' in line or '>' in line or '$' in line or '::' in line:
                            continue
                        if '(' not in line or ')' not in line:
                            continue
                        if test_file_name in line:
                            if ":" in line:
                                line_number = line.split(":")[1].split(")")[0]

        return line_number

    def initial_stage(self, bug_id, bug_func_name, bug_func_start_line, bug_func_end_line):

        logger.info('========== (Initial Stage) Process Bug {} ==============', bug_id)
        buggy_folder = os.path.join(self._save_folder, bug_id)

        if not os.path.exists(buggy_folder):
            os.makedirs(buggy_folder)
            logger.info("Create initial folder {}",buggy_folder)

        d4j_folder = os.path.join(buggy_folder, 'd4j_initial')
        if os.path.exists(d4j_folder):
            shutil.rmtree(d4j_folder)
        os.makedirs(d4j_folder)

        bf_folder = os.path.join(buggy_folder, 'BF')
        if os.path.exists(bf_folder):
            shutil.rmtree(bf_folder)
        os.makedirs(bf_folder)

        bs_folder = os.path.join(buggy_folder, 'BS')
        if os.path.exists(bs_folder):
            shutil.rmtree(bs_folder)
        os.makedirs(bs_folder)

        # Step 1: defects4j checkout & compile
        self._d4j_checkout(d4j_folder, bug_id)
        self._d4j_compile(d4j_folder, bug_id)

        tmp_folder = os.path.join(d4j_folder, 'contrast_tmp')
        if not os.path.exists(tmp_folder):
            os.makedirs(tmp_folder)

        # Step 2: assign parameters
        self._bug_record.id = bug_id
        self._bug_record.func_name = bug_func_name
        self._bug_record.d4j_initial = d4j_folder
        self._bug_record.tmp_folder = tmp_folder
        self._bug_record.BF = bf_folder
        self._bug_record.BS = bs_folder

        buggy_func_package, buggy_func_file_path = self._d4j_buggy_func(self._bug_record.d4j_initial)
        self._bug_record.buggy_func_package = buggy_func_package
        self._bug_record.buggy_func_file_path = buggy_func_file_path
        self._bug_record.buggy_func_method_name = bug_func_name
        self._bug_record.buggy_func_start_line = bug_func_start_line
        self._bug_record.buggy_func_end_line = bug_func_end_line
        self._bug_record.lib_package = self._d4j_lib_folder(self._bug_record.d4j_initial)

        # Step 3: instrument for our method
        self._jar_obtain_method_hash(self._bug_record.d4j_initial, self._bug_record)
        if not os.path.join(self._bug_record.tmp_folder, 'current_hash.txt'):
            logger.error("ManualCheck-{}-Hash", bug_id)
            return
        else:
            with open(os.path.join(self._bug_record.tmp_folder, 'current_hash.txt'), 'r') as f:
                line = f.readlines()[0].rstrip()
                curr_hash = int(line)

        if curr_hash == 0:
            logger.warning("ManualCheck-{}-Hash", bug_id)
            return
        else:
            self._bug_record.hash = curr_hash
        self._jar_instrument_write_before(self._bug_record.d4j_initial, self._bug_record)

        # Step 4: test all cases
        trigger_commands = self._d4j_triggers(self._bug_record.d4j_initial, self._bug_record.id)
        logger.debug(trigger_commands)
        repeat_dict = {}
        for tc in trigger_commands:
            logger.info('Command: {}', tc)
            self._bug_record.command = tc
            self._bug_record.test_case_package, self._bug_record.test_case_file_path, self._bug_record.test_case_method_name = self._d4j_test_case(self._bug_record.d4j_initial, tc)
            while True:
                run_res = Validation.preprocess_run_specific_test(d4j_folder, tc)
                if run_res == 0:
                    logger.info('Pass')
                    #todo: move to success
                    folders = sorted(glob.glob(os.path.join(self._bug_record.tmp_folder, 'seed_*')),
                                     key=lambda x: os.path.getmtime(x))
                    logger.debug('Success files: {}', len(folders))
                    for f_i in range(len(folders) - 1):
                        succ_case = folders[f_i]
                        succ_case_file_name = os.path.basename(succ_case)
                        target_success_file_path = os.path.join(self._bug_record.BS, succ_case_file_name)
                        shutil.copytree(folders[f_i], target_success_file_path)

                    shutil.rmtree(self._bug_record.tmp_folder)
                    os.makedirs(self._bug_record.tmp_folder)
                    break
                else:
                    test_case_error_line = self._parse_test_case_error_line_from_failing_log(d4j_folder, self._bug_record)

                    if test_case_error_line is None:
                        logger.warning("ManualCheck-{}-ErrorLine", bug_id)

                    self._bug_record.test_case_error_line = test_case_error_line
                    # mask test case
                    self._jar_mask_test_case(d4j_folder, self._bug_record)
                    test_mark_method = self._bug_record.test_case_file_path + \
                                       self._bug_record.test_case_method_name + \
                                       str(self._bug_record.test_case_error_line)

                    if test_mark_method not in repeat_dict:
                        repeat_dict[test_mark_method] = 0

                    repeat_dict[test_mark_method] += 1
                    if repeat_dict[test_mark_method] > 5:
                        logger.warning("ManualCheck-{}-TooTimes", bug_id)
                        shutil.rmtree(self._bug_record.tmp_folder)
                        os.makedirs(self._bug_record.tmp_folder)
                        break

                    if repeat_dict[test_mark_method] > 1:
                        shutil.rmtree(self._bug_record.tmp_folder)
                        os.makedirs(self._bug_record.tmp_folder)
                        continue

                    logger.debug('Type: {}', self._bug_record.type)
                    if self._bug_record.type != "Exception":
                        shutil.rmtree(self._bug_record.tmp_folder)
                        os.makedirs(self._bug_record.tmp_folder)
                        continue

                    # todo: move fails
                    folders = sorted(glob.glob(os.path.join(self._bug_record.tmp_folder, 'seed_*')),
                                     key=lambda x: os.path.getmtime(x))
                    if len(folders) == 0:
                        logger.warning("ManualCheck-{}-NoSaveFolder", bug_id)
                    else:
                        logger.info("==> Total files: {}", len(folders))
                        bug_case = folders[-1]  # the last one, new one
                        bug_case_file_name = os.path.basename(bug_case)
                        target_fail_file_path = os.path.join(self._bug_record.BF, bug_case_file_name)
                        logger.debug(target_fail_file_path)
                        shutil.copytree(bug_case, target_fail_file_path)

                    shutil.rmtree(tmp_folder)
                    os.makedirs(tmp_folder)

        with open(os.path.join(buggy_folder, self.INITIAL_JSON), 'w') as f:
            json.dump(asdict(self._bug_record), f, indent=4)

    def mutation_stage(self, bug_id):

        logger.info('========== (Mutation Stage) Process Bug {} ==============', bug_id)

        buggy_folder = os.path.join(self._save_folder, bug_id)
        if not os.path.exists(buggy_folder):
            logger.error('ErrorStage-No buggy folder {}', buggy_folder)
            return

        buggy_record_file = os.path.join(buggy_folder, self.INITIAL_JSON)
        if not os.path.isfile(buggy_record_file):
            logger.error('ErrorStage-No buggy record file {}, please initial this pre-process', buggy_record_file)
            return

        self._bug_record.get_one_from_json(buggy_record_file)

        folder_seeds = os.path.join(buggy_folder, 'mutation_seeds')  # save mutation seeds
        if os.path.exists(folder_seeds):
            shutil.rmtree(folder_seeds)
        os.makedirs(folder_seeds)
        self._bug_record.mutation = folder_seeds

        logger.debug('Start Mutation')

        fail_seeds = glob.glob(os.path.join(self._bug_record.BF, "seed_*"))
        if len(fail_seeds) == 0:
            logger.warning('No seeds -> No need mutation')

        for fail_seed_path in fail_seeds:
            logger.info('==> mutate for {}', fail_seed_path)
            cmd = f"java -jar {self._java_tool} " \
                  f"mutate {fail_seed_path} {folder_seeds}"
            logger.info(cmd)
            pmu = subprocess.Popen(cmd, shell=True)
            pmu.wait()

        # todo: save the config file
        with open(os.path.join(buggy_folder, self.MUTATION_JSON), 'w') as f:
            json.dump(asdict(self._bug_record), f, indent=4)

    def verification_stage(self, bug_id):

        logger.info('========== (Verify Stage) Process Bug {} ==============', bug_id)
        buggy_folder = os.path.join(self._save_folder, bug_id)
        if not os.path.exists(buggy_folder):
            logger.error('ErrorStage-No buggy folder {}', buggy_folder)
            return

        buggy_record_file = os.path.join(buggy_folder, self.MUTATION_JSON)
        if not os.path.isfile(buggy_record_file):
            logger.error('ErrorStage-No buggy record file {}, please initial this pre-process', buggy_record_file)
            return

        self._bug_record.get_one_from_json(buggy_record_file)

        logger.info('=> seeds from: {}', self._bug_record.mutation)

        as_folder = os.path.join(buggy_folder, 'AS')
        af_folder = os.path.join(buggy_folder, 'AF')

        if not os.path.exists(as_folder):
            os.makedirs(as_folder)
        if not os.path.exists(af_folder):
            os.makedirs(af_folder)

        self._bug_record.AS = as_folder
        self._bug_record.AF = af_folder

        d4j_folder = os.path.join(buggy_folder, 'd4j_verify')
        if os.path.exists(d4j_folder):
            shutil.rmtree(d4j_folder)
        os.makedirs(d4j_folder)

        self._bug_record.d4j_verify = d4j_folder
        self._bug_record.buggy_instrument = False

        # s1-1: checkout
        self._d4j_checkout(self._bug_record.d4j_verify, bug_id)
        # s1-2: compile
        self._d4j_compile(self._bug_record.d4j_verify, bug_id)

        # s2: insert
        jar_file_command_file = os.path.join(d4j_folder, 'seed_input_command.txt')
        with open(jar_file_command_file, 'w') as f:
            f.write('')
        self._bug_record.verify_command_file = jar_file_command_file

        logger.info('==> instrument method {} for {}', self._bug_record.hash, self._bug_record.id)
        self._jar_instrument_verify(self._bug_record.d4j_verify, self._bug_record)
        self._bug_record.buggy_instrument = True

        verify_input_parent_folder = self._bug_record.mutation
        logger.debug(verify_input_parent_folder)
        verify_input_folders = glob.glob(os.path.join(verify_input_parent_folder, 'mutation_*'))

        verify_log = os.path.join(buggy_folder, 'mutation_verify_log.json')
        self._bug_record.verify_log = verify_log

        if os.path.isfile(verify_log):
            with open(verify_log, 'r') as f:
                verify_dict = json.load(f)
        else:
            verify_dict = {}

        enter_case = False
        enter_tries = 0

        if len(verify_input_folders) == 0:
            logger.warning('No mutation -> No need verify')

        for vif in verify_input_folders:
            vif_name = os.path.basename(vif)
            vif = vif.rstrip()
            logger.info(vif)
            with open(jar_file_command_file, 'w') as f:
                f.write(str(vif))

            while not enter_case:
                enter_tries += 1
                if enter_tries > 5:
                    logger.error('ManualCheck-{}-NoEnterCase', bug_id)
                    return

                _ = Validation.preprocess_run_specific_test(self._bug_record.d4j_verify,
                                                                  self._bug_record.command)

                verify_txt_file = os.path.join(vif, "verifyResult.txt")
                if not os.path.isfile(verify_txt_file):
                    logger.warning('No verifyResult.txt, mask test case.')
                    self._jar_mask_test_case(self._bug_record.d4j_verify, self._bug_record)
                else:
                    enter_case = True

            run_res = Validation.preprocess_run_specific_test(self._bug_record.d4j_verify,
                                                              self._bug_record.command)
            if run_res != 0:
                verify_dict[vif_name] = 'fail'
                verify_txt_file = os.path.join(vif, "verifyResult.txt")
                if not os.path.isfile(verify_txt_file):
                    logger.warning('NoFile after success, please check.')
                    verify_dict[vif_name] = 'no-file'
            else:
                # success
                verify_txt_file = os.path.join(vif, "verifyResult.txt")
                if not os.path.isfile(verify_txt_file):
                    logger.warning('NoFile after success, please check.')
                    verify_dict[vif_name] = 'no-file'
                else:
                    with open(verify_txt_file, 'r') as f:
                        line = f.readline()
                        if line is None:
                            verify_dict[vif_name] = 'file-no-content'
                        else:
                            line = line.strip()
                            logger.debug('Line: {}', line)
                            if line == 'success':
                                verify_dict[vif_name] = 'success'
                            else:
                                verify_dict[vif_name] = 'uncertain'

            if verify_dict[vif_name] == 'success':
                seed_name = os.path.basename(vif)
                target_folder = os.path.join(as_folder, seed_name)
                if os.path.exists(target_folder):
                    shutil.rmtree(target_folder)
                shutil.move(vif, target_folder)
            else:
                seed_name = os.path.basename(vif)
                target_folder = os.path.join(af_folder, seed_name)
                if os.path.exists(target_folder):
                    shutil.rmtree(target_folder)
                shutil.move(vif, target_folder)

        with open(self._bug_record.verify_log, 'w') as f:
            json.dump(verify_dict, f, indent=4)

        with open(os.path.join(buggy_folder, self.VERIFY_JSON), 'w') as f:
            json.dump(asdict(self._bug_record), f, indent=4)