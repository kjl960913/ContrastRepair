import json
import os
import time
import signal
import openai
import tiktoken

from config import Config

from loguru import logger

def handler(signum, frame):
    raise Exception("ParameterFilter: end of time")

class ParameterFilter:

    def __init__(self, language='java'):
        self.name = 'ParameterFilter-{}'.format(language.lower())
        self._language = language
        self._max_try = 2
        self._system_role = "You are a Java code reviewer."
        self._model = "gpt-3.5-turbo"
        self._folder = os.path.join(Config.get_instance().result_folder, self.name)

        if not os.path.exists(self._folder):
            os.makedirs(self._folder)

        logger.info('{} folder is: {}', self.name, self._folder)

    @staticmethod
    def _create_config(message: str, temperature: float = 1, # default most diverse temperature
                       system_message: str = "You are a Java code expert."):
        return {
            "model": "gpt-3.5-turbo",
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": message.strip()}
            ]
        }

    @staticmethod
    def _chatgpt_parse_code(answer):
        # first check if its a code block
        if "```" in answer:
            func = answer.split("```")[1]
            func = "\n".join(func.split("\n")[1:])
            # basically saves previous history up until the last
            pre_history = "```".join(answer.split("```")[:2]) + "```"
        else:
            func, pre_history = "", ""
        return func, pre_history

    @staticmethod
    def _chatgpt_parse_check(answer):
        # yes -> contain error
        first_five = answer[:5]
        if 'yes' in first_five.lower():
            return False, None
        else:
            return True, None

    @staticmethod
    def _prompt(content, cls='extract'):
        if cls == 'extract':
            query = f"""
            You are a Java code expert. You can not update or modify codes. I will give you a Java method. The beginning of this method may contain return-based parameter validation. Return-based parameter validation has "return" keyword. Please check if the method contains return-based parameter validation. If so, please tell me the return-based parameter validation codes in an inline code formatting. The Java method is: ```{content}```
            """
        elif cls == 'fix':
            query = f"""In Java codes, return-line contains a key work "return". Return-line can be replaced by throwing Java exception. Please replace return-line in the following codes with throw Java exception. The codes are:  ```{content}```"""
        elif cls == 'check':
            query = f"""Please check whether my Java code snippet contains a syntax error or not. If it contains a syntax error, tell me 'yes' at the beginning of your response. Otherwise, tell me 'no' at the beginning of your response. My Java code snippet is: ```{content}```"""
        else:
            logger.error('Not support cls: {}', cls)
            raise KeyError('Not support cls in prompt.')
        return query

    @staticmethod
    def _query_gpt(gpt_config):
        ret = None
        while ret is None:
            try:
                logger.debug(ret)
                signal.signal(signal.SIGALRM, handler)
                signal.alarm(100)
                ret = openai.ChatCompletion.create(**gpt_config)
                logger.debug(ret)
                signal.alarm(0)  # cancel alarm
            except openai.error.InvalidRequestError as e:
                print(e)
                signal.alarm(0)  # cancel alarm
            except openai.error.RateLimitError as e:
                print("Rate limit exceeded. Waiting...")
                print(e)
                signal.alarm(0)  # cancel alarm
                time.sleep(5)  # wait for a minute
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
    def write_java_file(folder, patch, file_name):
        with open(os.path.join(folder, file_name), "w") as f:
            f.write(patch)

    @staticmethod
    def write_json_file(folder, ret, file_name):
        with open(os.path.join(folder, file_name), 'w') as f:
            json.dump(ret, f, indent=4)

    @staticmethod
    def inject_code(patch, source_code):
        source_code_lines = source_code.split('\n')
        patch_lines = patch.split('\n')
        fixed_code_lines = [source_code_lines[0]]
        fixed_code_lines += patch_lines
        fixed_code_lines += source_code_lines[1:]

        fixed_code = "\n".join(fixed_code_lines)
        return fixed_code

    def _check_patch(self, patch):
        logger.info('=====> check patch:')
        prompt = self._prompt(patch, 'check')
        gpt_query_config = self._create_config(message=prompt, system_message=self._system_role)
        for message in gpt_query_config['messages']:
            logger.info("{} : {}", message['role'], message['content'])
        ret = self._query_gpt(gpt_query_config)
        pass_flag, pre_history = self._chatgpt_parse_check(ret["choices"][0]['message']["content"])
        return pass_flag, ret

    def _fix_patch(self, patch):
        logger.info('=====> fix patch:')
        prompt = self._prompt(patch, 'fix')
        gpt_query_config = self._create_config(message=prompt, system_message=self._system_role)
        for message in gpt_query_config['messages']:
            logger.info("{} : {}", message['role'], message['content'])
        ret = self._query_gpt(gpt_query_config)
        func, pre_history = self._chatgpt_parse_code(ret["choices"][0]['message']["content"])
        return func, ret

    def _extract_patch(self, method_code):
        logger.info('=====> extract patch form method:')
        prompt = self._prompt(method_code, 'extract')
        gpt_query_config = self._create_config(message=prompt, system_message=self._system_role)
        for message in gpt_query_config['messages']:
            logger.info("{} : {}", message['role'], message['content'])
        ret = self._query_gpt(gpt_query_config)
        func, pre_history = self._chatgpt_parse_code(ret["choices"][0]['message']["content"])
        return func, ret

    def query(self, idx, method_code):
        logger.info('=====> Start ParameterFilter filter')
        tries = 0
        pass_flag = True
        locate_result = False
        gpt_queries_ret = []
        self.write_java_file(self._folder, method_code, str(idx) + "_original_method.java")
        fixed_method_code = method_code
        while True:
            if tries >= self._max_try:
                break
            ret_try = []
            logger.info('=====> Tries: {}', tries)
            func_patch, ret_extract = self._extract_patch(method_code)
            ret_try.append(ret_extract)
            ret_fix = None
            ret_check = None
            pass_flag = True # pass-True
            if func_patch != "":
                if self._language.lower() == 'java':
                    self.write_java_file(self._folder, func_patch, str(idx) + "_extract_patch_" + str(tries) +".java")
                    fixed_patch, ret_fix = self._fix_patch(func_patch)
                    if fixed_patch != "":
                        pass_flag, ret_check = self._check_patch(fixed_patch)
                        self.write_java_file(self._folder, fixed_patch, str(idx) + "_fixed_patch_" + str(tries) +".java")
                        fixed_method_code = self.inject_code(fixed_patch, method_code)
                        self.write_java_file(self._folder, fixed_method_code, str(idx) + "_fixed_method_" + str(tries) +".java")
                        locate_result = True
            ret_try.append(ret_fix)
            ret_try.append(ret_check)
            gpt_queries_ret.append(ret_try)
            if locate_result and pass_flag:
                break
            tries += 1

        self.write_json_file(self._folder, gpt_queries_ret, str(idx) + "_gpt_results.json")
        return locate_result, pass_flag, fixed_method_code

if __name__ == '__main__':
    openai.api_key = ''

    case = """private static int greatestCommonDivisor(int u, int v) {
        // From Commons Math:
        //if either operand is abs 1, return 1:
        if (Math.abs(u) <= 1 || Math.abs(v) <= 1) {
            return 1;
        }
        // keep u and v negative, as negative integers range down to
        // -2^31, while positive numbers can only be as large as 2^31-1
        // (i.e. we can't necessarily negate a negative number without
        // overflow)
        if (u>0) { u=-u; } // make u negative
        if (v>0) { v=-v; } // make v negative
        // B1. [Find power of 2]
        int k=0;
        while ((u&1)==0 && (v&1)==0 && k<31) { // while u and v are both even...
            u/=2; v/=2; k++; // cast out twos.
        }
        if (k==31) {
            throw new ArithmeticException("overflow: gcd is 2^31");
        }
        // B2. Initialize: u and v have been divided by 2^k and at least
        //     one is odd.
        int t = ((u&1)==1) ? v : -(u/2)/*B3*/;
        // t negative: u was odd, v may be even (t replaces v)
        // t positive: u was even, v is odd (t replaces u)
        do {
            /* assert u<0 && v<0; */
            // B4/B3: cast out twos from t.
            while ((t&1)==0) { // while t is even..
                t/=2; // cast out twos
            }
            // B5 [reset max(u,v)]
            if (t>0) {
                u = -t;
            } else {
                v = t;
            }
            // B6/B3. at this point both u and v should be odd.
            t = (v - u)/2;
            // |u| larger: t positive (replace u)
            // |v| larger: t negative (replace v)
        } while (t!=0);
        return -u*(1<<k); // gcd is u*2^k
    }"""

    pf = ParameterFilter()
    pf.query(7, case)
