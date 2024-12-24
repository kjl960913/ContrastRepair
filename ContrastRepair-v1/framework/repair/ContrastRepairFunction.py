import copy
import os
import json
import re
import time
import shutil
import signal
import openai
import tiktoken
from datetime import datetime
from typing import Dict
from difflib import unified_diff
from loguru import logger
from dataclasses import dataclass
from framework.repair.PromptCreator import PromptCreator
from framework.repair.ChatParser import ChatParser
from framework.runner.Validation import Validation
from framework.selection.FuzzRanker import FuzzRanker
from config import Config

def handler(signum, frame):
    raise Exception("end of time")

def get_unified_diff(source, mutant):
    output = ""
    for line in unified_diff(source.split('\n'), mutant.split('\n'), lineterm=''):
        output += line + "\n"
    return output

@dataclass
class ContrastRepairFunction:

    _total_tries: int
    _chain_length: int
    _max_tokens: int
    _save_folder: str

    prompter: PromptCreator = PromptCreator()

    def __init__(self, total_tries: int, repeats: int, repeat_mode:str, pair_type: str, chatgpt_parser:str):
        self._total_tries = total_tries
        self._repeats = repeats
        self._repeat_mode = repeat_mode
        self._pair_type = pair_type
        assert self._pair_type in ['no', 'exception', 'assert', 'both']
        # self._corpus_update_frequency = corpus_update_frequency
        if self._repeat_mode not in ['same', 'iterative']:
            logger.error('Unsupported repeat mode: {}', self._repeat_mode)
            raise KeyError()
        self._use_last = True if self._repeat_mode == 'iterative' else False
        self._results = {}
        self._gpt_record = {}
        self._config = Config.get_instance()
        self._save_folder = self._config.result_folder # os.path.join(self._config.result_folder, 'repair')
        if not os.path.exists(self._save_folder):
            os.makedirs(self._save_folder)
        else:
            logger.warning('{} exists.', self._save_folder)

        self._dynamic_case_folder = os.path.join(self._save_folder, 'cases')
        if not os.path.exists(self._dynamic_case_folder):
            os.makedirs(self._dynamic_case_folder)

        self._chatgpt_parser = ChatParser(chatgpt_parser)
        self._prompt = PromptCreator()
        self._validator = Validation()
        self._case_corpus_pool: Dict[FuzzRanker] = dict()

    def _load_case_corpus(self, bug_id):
        # now = datetime.now()
        # date_time = now.strftime("%m-%d-%Y-%H-%M-%S")
        source_case_pair_file = os.path.join(self._config.case_folder, bug_id + '.json')
        # if not os.path.exists(source_case_pair_file):
        #     return None
        # target_case_pair_file = os.path.join(self._dynamic_case_folder, bug_id + '_' + date_time + '.json')
        # shutil.copy(source_case_pair_file, target_case_pair_file)
        assert_file_path = os.path.join(self._config.case_folder, bug_id + '_Assert.json')

        if self._pair_type == 'assert' and (not os.path.exists(assert_file_path)):
            return None

        if self._pair_type == 'exception' and (not os.path.exists(source_case_pair_file)):
            return None

        if (not os.path.exists(assert_file_path)) and (not os.path.exists(source_case_pair_file)):
            return None

        if not os.path.exists(assert_file_path):
            assert_file_path = None

        if not os.path.exists(source_case_pair_file):
            source_case_pair_file = None

        return FuzzRanker(self._pair_type, source_case_pair_file, assert_file_path,
                          self._config.pair_prob_fail, self._config.pair_prob_succ)

    def _update_case_corpus(self, bug_id):
        now = datetime.now()
        date_time = now.strftime("%m-%d-%Y-%H-%M-%S")
        source_case_pair_file = os.path.join(self._config.case_folder, bug_id + '.json')
        target_case_pair_file = os.path.join(self._dynamic_case_folder, bug_id + '_' + date_time + '.json')
        shutil.copy(source_case_pair_file, target_case_pair_file)

    @staticmethod
    def _request_chatgpt_engine(config):
        ret = None
        count = 0
        while ret is None:
            if count > 10:
                return ret
            count += 1
            # ret = openai.ChatCompletion.create(**config)
            try:
                ret = openai.ChatCompletion.create(**config)
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(100)
                # ret = openai.ChatCompletion.create(**config)
                signal.alarm(0)  # cancel alarm
            except openai.error.InvalidRequestError as e:
                print(e)
                signal.alarm(0)  # cancel alarm
            except openai.error.RateLimitError as e:
                print("Rate limit exceeded. Waiting...")
                print(e)
                signal.alarm(0)  # cancel alarm
                time.sleep(60)  # wait for a minute
            except openai.error.APIConnectionError as e:
                print("API connection error. Waiting...")
                signal.alarm(0)  # cancel alarm
                time.sleep(5)  # wait for a minute
            except Exception as e:
                print(e)
                print("Unknown error. Waiting...")
                signal.alarm(0)  # cancel alarm
                time.sleep(1)  # wait for a minute
        return ret

    @staticmethod
    def _num_tokens_from_messages(messages, model="gpt-3.5-turbo-0301"):
        """Returns the number of tokens used by a list of messages."""
        try:
            encoding = tiktoken.encoding_for_model(model)
        except KeyError:
            encoding = tiktoken.get_encoding("cl100k_base")
        if model == "gpt-3.5-turbo-0301":  # note: future models may deviate from this
            num_tokens = 0
            for message in messages:
                num_tokens += 4  # every message follows <im_start>{role/name}\n{content}<im_end>\n
                for key, value in message.items():
                    num_tokens += len(encoding.encode(value))
                    if key == "name":  # if there's a name, the role is omitted
                        num_tokens += -1  # role is always required and always 1 token
            num_tokens += 2  # every reply is primed with <im_start>assistant
            return num_tokens
        else:
            raise NotImplementedError(f"""num_tokens_from_messages() is not presently implemented for model {model}. See 
            https://github.com/openai/openai-python/blob/main/chatml.md for information on how messages are converted to 
            tokens.""")

    @staticmethod
    def _chatgpt_config(prev:dict, message: str, max_tokens: int = 4096, temperature: float = 1,
                        system_message: str = "You are a Java code program repair expert. ",
                        use_last: bool = False, last_answer: str = ""):
        if Config().dataset == 'quixbugs-python':
            system_message = "You are a Python code program repair expert. "
        if not use_last:
            return {
                "model": "gpt-3.5-turbo-0301",
                # "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": message.strip()}
                ]
            }
        else:
            prev["messages"].append({"role": "assistant", "content": last_answer})
            prev["messages"].append({"role": "user", "content": message.strip()})
            return prev

    @staticmethod
    def remove_comments(string):
        pattern = r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)"
        # first group captures quoted strings (double or single)
        # second group captures comments (//single-line or /* multi-line */)
        regex = re.compile(pattern, re.MULTILINE | re.DOTALL)

        def _replacer(match):
            # if the 2nd group (capturing comments) is not None,
            # it means we have captured a non-quoted (real) comment string.
            if match.group(2) is not None:
                return ""  # so we will return empty to remove the comment
            else:  # otherwise, we will return the 1st group
                return match.group(1)  # captured quoted-string

        return regex.sub(_replacer, string)

    def _save_tmp_gpt_results(self):
        with open(os.path.join(self._save_folder, "tmp_results.json"), "w") as f:
            json.dump(self._results, f, indent=4)

        with open(os.path.join(self._save_folder, "tmp_gpt_records.json"), "w") as f:
            json.dump(self._gpt_record, f, indent=4)

    def repair(self, bugs):
        sys_config = Config()
        # flag = False
        for bug, bug_js in bugs.items():
            # Step1: check token length and sample initialization
            if sys_config.dataset == 'quixbugs-java':
                bug_id = bug + '_TEST'
            elif sys_config.dataset == 'quixbugs-python':
                bug_id = 'test_' + bug
            else:
                bug_id = bug.split('.')[0]
            # if bug_id == "Lang-27":
            #     flag = True
            # if not flag:
            #     continue

            logger.info("====> Repair Bug: {}".format(bug_id))
            if bug_id not in self._case_corpus_pool.keys():
                corpus = self._load_case_corpus(bug_id)
                if corpus is None:
                    logger.warning('====> No files of bug: {}. Continue', bug_id)
                    continue
                self._case_corpus_pool[bug_id] = corpus
                logger.info("====> {} case corpus created {}.", bug_id, corpus)

            self._results[bug] = []
            self._gpt_record[bug] = []
            generations = {}  # keep the previous generation, save validation time
            tries = 0
            true_valid = False
            reset = True
            while tries < self._total_tries and not true_valid:
                tries += 1

                # dict {type, fail, success}
                try:
                    select_pairs = self._case_corpus_pool[bug_id].selection(self._config.pairs, self._config.top_k)
                except Exception as e:
                    print(e)
                    continue

                # add by  7/8 if the length of token is too long, remove part of it to let it be less than 4096
                if sys_config.dataset.startswith('quixbugs'):
                    # judge the bugs are from Quix-Java or Quix-Python
                    tmp_prompt = self._prompt.get_initial_prompt4quix(bug_js['buggy'], select_pairs, "SF", bug_js)
                else:
                    tmp_prompt = self._prompt.get_initial_prompt(bug_js['buggy'], select_pairs, 'SF', bug_js)
                if_have_exception_success, if_have_assert_success = False, False
                tmp_SF_list = None
                Assert_Success, Exception_Success, Assert_Fail, Exception_Fail = [], [], [], []
                for error_dict in select_pairs:
                    if error_dict["type"] == "Exception":
                        if not len(error_dict["success"]) == 0:
                            if_have_exception_success = True
                            Exception_Success = error_dict["success"]
                        Exception_Fail = error_dict['fail']

                    if error_dict["type"] == "Assert":
                        if not len(error_dict["success"]) == 0:
                            if_have_assert_success = True
                            Assert_Success = error_dict["success"]
                        Assert_Fail = error_dict['fail']
                tmp_SF_list = Assert_Success + Exception_Success + Assert_Fail + Exception_Fail

                tmp_prompt_dict = {'message': tmp_prompt}
                tmp_prompt_tokens_list = []
                tmp_prompt_tokens_list.append(tmp_prompt_dict)
                max_tokens = self._num_tokens_from_messages(tmp_prompt_tokens_list)
                remove_times = 0
                if max_tokens > 4000:
                    temp_tokens = max_tokens

                    #After removing, record the value of remove_time, and remove in select_pairs
                    count = 0
                    try:
                        while temp_tokens >= 4000 and count < 200:
                            count += 1

                            if sys_config.dataset.startswith('quixbugs'):
                                # judge the bugs are from Quix-Java or Quix-Python
                                tmp_token_str = self._prompt.get_initial_prompt4quix(bug_js['buggy'], select_pairs, "SF", bug_js)
                            else:
                                tmp_token_str = self._prompt.get_initial_prompt(bug_js['buggy'], select_pairs, 'SF', bug_js)
                            tmp_json_tokens_dict = {'message': tmp_token_str}
                            tmp_json_tokens_list = [tmp_json_tokens_dict]
                            temp_tokens = self._num_tokens_from_messages(tmp_json_tokens_list)

                            for error_dict in select_pairs:
                                if error_dict['type'] == "Assert":
                                    if len(error_dict['fail']) > 0:
                                        str_case_to_modify = error_dict['fail'][0][0]
                                        str_lens = len(str_case_to_modify)
                                        if str_lens == 0:
                                            error_dict['fail'].pop(0)
                                        else:
                                            tmp_str = error_dict['fail'][0][0]
                                            tmp_list = tmp_str.split('\n')
                                            error_dict['fail'][0][0] = "\n".join(tmp_list[:-1])
                                        break_flag3 = True
                                        break
                            if break_flag3:
                                continue
                            for error_dict in select_pairs:
                                if error_dict['type'] == "Exception":
                                    if len(error_dict['fail']) > 0:
                                        str_case_to_modify = error_dict['fail'][0][0]
                                        str_lens = len(str_case_to_modify)
                                        if str_lens == 0:
                                            error_dict['fail'].pop(0)
                                        else:
                                            tmp_str = error_dict['fail'][0][0]
                                            tmp_list = tmp_str.split('\n')
                                            error_dict['fail'][0][0] = "\n".join(tmp_list[:-1])
                                        break_flag4 = True
                                        break
                            if break_flag4:
                                continue

                            if if_have_assert_success:
                                for error_dict in select_pairs:
                                    if error_dict['type'] == "Assert":
                                        if len(error_dict['success']) > 0:
                                            str_case_to_modify = error_dict['success'][0][0]
                                            str_lens = len(str_case_to_modify)
                                            if str_lens == 0:
                                                error_dict['success'].pop(0)
                                            else:
                                                tmp_str = error_dict['success'][0][0]
                                                tmp_list = tmp_str.split('\n')
                                                error_dict['success'][0][0] = "\n".join(tmp_list[:-1])
                                            break_flag1 = True
                                            break
                                if break_flag1:
                                    continue
                            if if_have_exception_success:
                                for error_dict in select_pairs:
                                    if error_dict['type'] == "Exception":
                                        if len(error_dict['success']) > 0:
                                            str_case_to_modify = error_dict['success'][0][0]
                                            str_lens = len(str_case_to_modify)
                                            if str_lens == 0:
                                                error_dict['success'].pop(0)
                                            else:
                                                tmp_str = error_dict['success'][0][0]
                                                tmp_list = tmp_str.split('\n')
                                                error_dict['success'][0][0] = "\n".join(tmp_list[:-1])
                                            break_flag2 = True
                                            break
                                if break_flag2:
                                    continue

                    except Exception as e:
                        print(e)
                        logger.debug('Error happens while remove the excessive part of prompt to let it less than 4096!')
                        break
                    logger.debug('First check tokens length and find excess max_tokens 4096 with {}.', max_tokens)
                    print('First check tokens length and find excess max_tokens 4096 with {}.', max_tokens)

                logger.debug('select pairs: {}', len(select_pairs))
                if sys_config.dataset.startswith('quixbugs'):
                    # judge the bugs are from Quix-Java or Quix-Python
                    curr_prompt = self._prompt.get_initial_prompt4quix(bug_js['buggy'], select_pairs, "SF", bug_js)
                else:
                    curr_prompt = self._prompt.get_initial_prompt(bug_js['buggy'], select_pairs, 'SF', bug_js)
                # 2.3 create initial chatgpt config
                # gpt_config = self._chatgpt_config(prev={}, message=curr_prompt, max_tokens=self._max_tokens, use_last=False)
                # max_tokens = self._num_tokens_from_messages(gpt_config["messages"]) + self._max_tokens
                #
                curr_prompt_dict = {}
                curr_prompt_dict["message"] = curr_prompt
                curr_prompt_dict_list = []
                curr_prompt_dict_list.append(curr_prompt_dict)
                max_tokens = self._num_tokens_from_messages(curr_prompt_dict_list)
                if max_tokens > 4096:
                    logger.debug('Excess max_tokens 4096 with {}.', max_tokens)
                    break
                    # return False
                syntax_count = 0
                repeated_bad = False
                prompt_times = 0
                while prompt_times < self._repeats:
                    prompt_times += 1
                    logger.info('Tries: {} Prompt_times: {}', tries, prompt_times)
                    gpt_config = self._chatgpt_config(prev={}, message=curr_prompt, use_last=False, temperature=self._config.temperature)

                    logger.debug('Request: ')
                    for message in gpt_config['messages']:
                        logger.debug("{} : {}", message['role'], message['content'])

                    ret = self._request_chatgpt_engine(gpt_config)
                    if ret is None:
                        continue

                    # todo: improve this part
                    answer = ret["choices"][0]['message']["content"]
                    logger.info('Response:')
                    logger.info(answer)
                    func, last_answer = self._chatgpt_parser.chatgpt_parse(answer)

                    logger.info('ParseFunc:')
                    logger.info(func)

                    self._gpt_record[bug].append(
                        {'id': str(bug_id) + '-' + str(tries) + '-' + str(prompt_times),
                         'patch': func, "prompt": gpt_config, "prompt_times": prompt_times,
                         'tries': tries, "usage": ret['usage'], 'output': ret}
                    )
                    self._save_tmp_gpt_results()

                    if func != "":
                        # output = v['prefix'] + "\n" + func.strip() + "\n" + v['suffix']
                        output = func
                        logger.debug('Modification: {}', get_unified_diff(bug_js['buggy'], output))
                        if output not in generations:
                            patch_folder = os.path.join(self._save_folder, 'patches')
                            if not os.path.exists(patch_folder):
                                os.makedirs(patch_folder)
                            try:
                                if sys_config.dataset.startswith('quixbugs'):
                                    type = 'java' if sys_config.dataset == 'quixbugs-java' else 'python'
                                    file_name = bug + "_{}.java".format(len(generations)) if sys_config.dataset == 'quixbugs-java' else bug + "_{}.python".format(len(generations))
                                    valid, error_message = self._validator._write_file4quix(patch_folder, output, file_name, bug, lang=type)
                                else:
                                    valid, error_message = self._validator.write_file(patch_folder, output,
                                                                                  bug.split(".java")[0] + "_{}.java".format(len(generations)),
                                                                                  bug.split(".java")[0], skip_val=False,
                                                                                  lang='java',
                                                                                  reset=reset)
                            except Exception as e:
                                print(e)
                                break

                            generations[output] = error_message
                            if reset:
                                reset = False
                        else:
                            valid = False
                            error_message = generations[output]

                        logger.info('ErrorMessage: {}', error_message)

                        self._results[bug].append(
                            {'id': str(bug_id) + '-' + str(tries) + '-' + str(prompt_times),
                             'patch': func, 'valid': valid, "prompt": gpt_config, "prompt_times": prompt_times,
                             'tries': tries, "usage": ret['usage'], "error": error_message, 'output': ret}
                        )
                        self._save_tmp_gpt_results()

                        logger.info('ResultsLength: {}', len(self._results[bug]))
                        if valid:
                            true_valid = True
                            break

                        # update curr_prompt
                        try:
                            select_pairs = self._case_corpus_pool[bug_id].selection(self._config.pairs, self._config.top_k)
                        except Exception as e:
                            logger.info("Error happens when selecting pairs!")
                            continue

                        #@ todo: check func -> if '' drop and continue or if diff > large number?
                        if sys_config.dataset.startswith('quixbugs'):
                            # judge the bugs are from Quix-Java or Quix-Python
                            curr_prompt = self._prompt.get_iterative_prompt4quix(func, select_pairs,
                                                                                 error_message, bug_js, "SF")
                        else:
                            curr_prompt = self._prompt.get_iterative_prompt(func, select_pairs, error_message, bug_js)

                        # add by  7/9 remove excessive part tokens in round prompt
                        tmp_prompt_dict = {'message': curr_prompt}
                        tmp_prompt_tokens_list = [tmp_prompt_dict]
                        max_tokens = self._num_tokens_from_messages(tmp_prompt_tokens_list)

                        if max_tokens > 4000:
                            temp_tokens = max_tokens
                            count = 0
                            try:
                                while temp_tokens >= 4000 and count < 200:
                                    count += 1
                                    if sys_config.dataset.startswith('quixbugs'):
                                        # judge the bugs are from Quix-Java or Quix-Python
                                        tmp_token_str = self._prompt.get_iterative_prompt4quix(func, select_pairs,
                                                                                             error_message, bug_js, "SF")
                                    else:
                                        tmp_token_str = self._prompt.get_iterative_prompt(func, select_pairs, error_message, bug_js)
                                    tmp_json_tokens_dict = {'message': tmp_token_str}
                                    tmp_json_tokens_list = [tmp_json_tokens_dict]
                                    temp_tokens = self._num_tokens_from_messages(tmp_json_tokens_list)

                                    for error_dict in select_pairs:
                                        if error_dict['type'] == "Assert":
                                            if len(error_dict['fail']) > 0:
                                                str_case_to_modify = error_dict['fail'][0][0]
                                                str_lens = len(str_case_to_modify)
                                                if str_lens == 0:
                                                    error_dict['fail'].pop(0)
                                                else:
                                                    tmp_str = error_dict['fail'][0][0]
                                                    tmp_list = tmp_str.split('\n')
                                                    error_dict['fail'][0][0] = "\n".join(tmp_list[:-1])
                                                break_flag3 = True
                                                break
                                    if break_flag3:
                                        continue
                                    for error_dict in select_pairs:
                                        if error_dict['type'] == "Exception":
                                            if len(error_dict['fail']) > 0:
                                                str_case_to_modify = error_dict['fail'][0][0]
                                                str_lens = len(str_case_to_modify)
                                                if str_lens == 0:
                                                    error_dict['fail'].pop(0)
                                                else:
                                                    tmp_str = error_dict['fail'][0][0]
                                                    tmp_list = tmp_str.split('\n')
                                                    error_dict['fail'][0][0] = "\n".join(tmp_list[:-1])
                                                break_flag4 = True
                                                break
                                    if break_flag4:
                                        continue

                                    if if_have_assert_success:
                                        for error_dict in select_pairs:
                                            if error_dict['type'] == "Assert":
                                                if len(error_dict['success']) > 0:
                                                    str_case_to_modify = error_dict['success'][0][0]
                                                    str_lens = len(str_case_to_modify)
                                                    if str_lens == 0:
                                                        error_dict['success'].pop(0)
                                                    else:
                                                        tmp_str = error_dict['success'][0][0]
                                                        tmp_list = tmp_str.split('\n')
                                                        error_dict['success'][0][0] = "\n".join(tmp_list[:-1])
                                                    break_flag1 = True
                                                    break
                                        if break_flag1:
                                            continue
                                    if if_have_exception_success:
                                        for error_dict in select_pairs:
                                            if error_dict['type'] == "Exception":
                                                if len(error_dict['success']) > 0:
                                                    str_case_to_modify = error_dict['success'][0][0]
                                                    str_lens = len(str_case_to_modify)
                                                    if str_lens == 0:
                                                        error_dict['success'].pop(0)
                                                    else:
                                                        tmp_str = error_dict['success'][0][0]
                                                        tmp_list = tmp_str.split('\n')
                                                        error_dict['success'][0][0] = "\n".join(tmp_list[:-1])
                                                    break_flag2 = True
                                                    break
                                        if break_flag2:
                                            continue

                            except Exception as e:
                                print(e)
                                logger.debug(
                                    'Error happens while remove the excessive part of Round-Prompt to let it less than 4096!')
                                continue
                            logger.debug('Check tokens length in Round-Prompt and find excess max_tokens 4096 with {}.',
                                         max_tokens)
                            print('Check tokens length in Round-Prompt and find excess max_tokens 4096 with {}.', max_tokens)

                        logger.debug('select pairs: {}', len(select_pairs))
                        if sys_config.dataset.startswith('quixbugs'):
                            # judge the bugs are from Quix-Java or Quix-Python
                            curr_prompt = self._prompt.get_iterative_prompt4quix(func, select_pairs,
                                                                                   error_message, bug_js, "SF")
                        else:
                            curr_prompt = self._prompt.get_iterative_prompt(func, select_pairs, error_message, bug_js)
                        #--------------------------

                        if error_message[0] == "SyntaxError" or error_message[0] == "CompileError":
                            syntax_count += 1
                        elif "[javac]" in error_message[0] or "[exec]" in error_message[0]:  # todo check exec
                            syntax_count += 1
                    else:
                        syntax_count += 1

                    logger.debug('syntax_count: {}', syntax_count)
                    if syntax_count >= 2:
                        repeated_bad = True
                    else:
                        repeated_bad = False

                    if repeated_bad:
                        break

        with open(os.path.join(self._save_folder, sys_config.dataset+"SF_final_results.json"), "w") as f:
            json.dump(self._results, f, indent=4)

        with open(os.path.join(self._save_folder, sys_config.dataset+"SF_gpt_records.json"), "w") as f:
            json.dump(self._gpt_record, f, indent=4)

    def plausible_to_correct(self, bugs):
        INFILL_TOKEN = ">>> [ INFILL ] <<<"
        max_tokens = 100
        with open(os.path.join(self._save_folder, "plausible_patches.json"), "r") as f:
            plausible_fixes = json.load(f)
            # underlying assumption is that there should be on plausible fix
            # and is computed using chatgpt

        results = {}
        plausible_list = ['Chart-13.java', 'Chart-3.java', 'Chart-5.java', 'Closure-104.java', 'Closure-107.java']
        for bug, v in plausible_fixes.items():
            bug_js = bugs[bug]
            if bug not in plausible_list:
                continue
            print(bug)
            plausible_patch = ""
            for patch in v:
                if patch['valid']:
                    plausible_patch = patch['patch']
                    starting_try = patch['tries']
                    break
            if plausible_patch != "":
                prompt = self._prompt.INIT_CHATGPT_FUNCTION_PFC_PROMPT.format(
                    buggy_code=bugs[bug]['buggy'],
                    patch_function=plausible_patch.strip(),
                    failing_test=bugs[bug]['failing_tests'][0]['test_method_name'],
                    error_message=bugs[bug]['failing_tests'][0]['failure_message'].strip(),
                    failing_line=bugs[bug]['failing_tests'][0]['failing_line'].strip()
                ).strip()
                # print(prompt)
                results[bug] = []
                generations = {}
                # tries = max(starting_try, 180)
                tries = 0
                reset = True
                num_plausible = 1
                while tries < 60:
                    fake_message = [{"role": "system", "content": bugs[bug]['buggy']}]
                    max_tokens = int(self._num_tokens_from_messages(fake_message) * 1.5)
                    config = self._chatgpt_config(prev={}, message=prompt + "\n" + self._prompt.PFC_SUFFIX_FUNCTION_PROMPT,
                                                  use_last=False, temperature=self._config.temperature)
                    if self._num_tokens_from_messages(config["messages"]) + max_tokens > 4096:
                        break
                    for message in config['messages']:
                        print("{} : {}".format(message['role'], message['content']))
                    print("Tries: {} Tokens: {}".format(tries, self._num_tokens_from_messages(config["messages"])))
                    ret = self._request_chatgpt_engine(config)
                    tries += 1

                    func, pre_history = self._chatgpt_parser.chatgpt_parse(ret["choices"][0]['message']["content"])
                    func = self.remove_comments(func)
                    if func != "":
                        output = func
                        diff = get_unified_diff(self.remove_comments(plausible_patch), func.strip())
                        if diff == "":
                            continue
                        print(output)

                        if output.replace(" ", "") not in generations:
                            # output = bug_js['prefix'] + "\n" + func.strip() + "\n" + bug_js['suffix']
                            logger.debug('Modification: {}', get_unified_diff(bug_js['buggy'], output))
                            patch_folder = os.path.join(self._save_folder, 'patchesP2C')
                            if not os.path.exists(patch_folder):
                                os.makedirs(patch_folder)
                            try:
                                valid, error_message = self._validator.write_file(patch_folder, output,
                                                       bug.split(".java")[0] + "_{}.java".format(len(generations)),
                                                       bug.split(".java")[0], skip_val=False,
                                                       lang='java',
                                                       reset=reset)
                            except Exception as e:
                                print(e)
                                continue

                            generations[output.replace(" ", "")] = valid
                            if reset:
                                reset = False
                            if valid:
                                num_plausible += 1
                        else:
                            valid = generations[output.replace(" ", "")]
                        results[bug].append(
                            {'patch': func, 'valid': valid, "prompt": config,
                             'tries': tries, "usage": ret['usage'], 'output': ret})

            with open(os.path.join(self._save_folder, "plausible2correct_SF.json"), "w") as f:
                json.dump(results, f)