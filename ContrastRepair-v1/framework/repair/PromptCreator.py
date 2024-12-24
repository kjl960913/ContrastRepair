from dataclasses import dataclass, asdict

from loguru import logger

INFILL_TOKEN = ">>> [ INFILL ] <<<"


@dataclass
class PromptCreator:
    exception_pair_unit_success: str = """Input Parameters: {success_case} -> Result: Correct\n"""
    exception_pair_unit_fail: str = """Input Parameters: {fail_case} -> Result: Exception Error\n"""
    exception_pair_unit_case: str = """Input Parameters: {case}\n"""

    assert_pair_unit_success: str = """Assert Test: {success_case} -> Result: Correct\n"""
    assert_pair_unit_fail: str = """Assert Test: {fail_case} -> Result: Assertion Failed Error\n"""
    assert_pair_unit_case: str = """Assert Test: {case}\n"""

    # with pair
    pair_prompt_initial_w_pair: str = """
    The following Java function contains bugs:```\n{buggy_code}```\nThe test case information is:\n{test_log}\n
    The code fails on this test: `{failing_test}()`
    on this test line: `{failing_line}`
    with the following test error: {error_message}
    Please fix bugs in the Java function, and tell me the complete fixed Java function.
    """

    pair_prompt_round_w_pair: str = """
    The following Java function contains bugs:```\n{buggy_code}```\nBugs are:\n1. {bugs};\n2. The test case information is:\n{test_cases}\nPlease fix bugs in the Java function, and tell me the complete fixed Java function.
    """

    # without pair
    pair_prompt_initial_wo_pair: str = """
    The following Java function contains bugs:```\n{buggy_code}```\n
    The code fails on this test: `{failing_test}()`
    on this test line: `{failing_line}`
    with the following test error: {error_message}
    Please fix bugs in the Java function, and tell me the complete fixed Java function.
    """

    pair_prompt_round_wo_pair: str = """
       The following Java function contains bugs:```\n{buggy_code}```\nBugs are:\n{bugs}.\nPlease fix bugs in the Java function, and tell me the complete fixed Java function.
       """

    INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE = """
    The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

The test case information is:\n{test_log}

Please provide the correct code hunk at the infill location.
"""

    INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_WO_PAIR = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

Please provide the correct code hunk at the infill location.
"""

    INIT_CHATGPT_INFILL_FAILING_TEST_LINE = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

The test case information is:\n{test_log}

Please provide the correct line at the infill location.
"""

    INIT_CHATGPT_INFILL_FAILING_TEST_LINE_WO_PAIR = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

Please provide the correct line at the infill location.
"""

    # add by  template for QuixBugs_Java/Python

    INIT_CHATGPT_INFILL_FAILING_TEST_LINE_QUIX = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_line}
```
The feedback message is: `{error_message}`

The test case information is:\n{test_log}

Please provide the correct line at the infill location.
"""

    INIT_CHATGPT_INFILL_FAILING_TEST_LINE_WO_PAIR_QUIX = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_line}
```
The feedback message is: `{error_message}`

Please provide the correct line at the infill location.
"""

    INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_QUIX = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
The feedback message is: `{error_message}`

The test case information is:\n{test_log}

Please provide the correct code hunk at the infill location.
"""

    INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_WO_PAIR_QUIX = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
The feedback message is: `{error_message}`

Please provide the correct code hunk at the infill location.
"""

    pair_prompt_initial_w_pair_QUIX: str = """
The following function contains bugs:```\n{buggy_code}```\n
The feedback message is: `{error_message}`
The test case information is:\n{test_log}\n
Please fix bugs in the function, and tell me the complete fixed function.
"""

    # without pair
    pair_prompt_initial_wo_pair_QUIX: str = """
The following Java function contains bugs:```\n{buggy_code}```\n
The feedback message is: `{error_message}`
Please fix bugs in the function, and tell me the complete fixed function.
"""

    # ---------------------Templates plausible2correct----------------------------

    INIT_CHATGPT_INFILL_LINE_PFC_PROMPT = """
The following code contains a buggy line that has been removed.
```
{buggy_code}
```
This was the original buggy line which was removed by the infill location
```
// buggy line
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

It can be fixed by these hunk
1.
```
{fix_hunk}
```
"""

    PFC_ADD_PROMPT = """
{num}.
```
{fix_hunk}
```
"""

    PFC_SUFFIX_LINE_PROMPT = "Please generate an alternative fix line at the infill location."

    INIT_CHATGPT_INFILL_PFC_PROMPT = """
The following code contains a buggy hunk that has been removed.
```
{buggy_code}
```
This was the original buggy hunk which was removed by the infill location
```
// buggy hunk
{buggy_hunk}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

It can be fixed by these hunks
1.
```
{fix_hunk}
```
"""

    PFC_SUFFIX_PROMPT = "Please generate an alternative fix hunk at the infill location."

    INIT_CHATGPT_FUNCTION_PFC_PROMPT = """
The following code contains a bug.
```
{buggy_code}
```
The code fails on this test: `{failing_test}()`
on this test line: `{failing_line}`
with the following test error: {error_message}

It can be fixed by this patch function
```
{patch_function}
```
"""

    PFC_SUFFIX_FUNCTION_PROMPT = "Please generate an alternative fix function."

    def _build_initial_test_log(self, test_pairs):
        test_log = ''
        for cls_pairs in test_pairs:
            pair_type = cls_pairs['type']
            if pair_type == 'Exception':
                for f_item in cls_pairs['fail']:
                    test_log += self.exception_pair_unit_fail.format(
                        fail_case=str(f_item).replace('[', '').replace(']', ''))
                for s_item in cls_pairs['success']:
                    test_log += self.exception_pair_unit_success.format(
                        success_case=str(s_item).replace('[', '').replace(']', ''))
            elif pair_type == 'Assert':
                for f_item in cls_pairs['fail']:
                    test_log += self.assert_pair_unit_fail.format(
                        fail_case=str(f_item).replace('[', '').replace(']', ''))
                for s_item in cls_pairs['success']:
                    test_log += self.assert_pair_unit_success.format(
                        success_case=str(s_item).replace('[', '').replace(']', ''))
            else:
                logger.error('Not support pair type: {}', pair_type)
                raise KeyError()

        return test_log

    def _build_round_test_log(self, test_pairs):
        test_cases = ''
        for cls_pairs in test_pairs:
            pair_type = cls_pairs['type']
            if pair_type == 'Exception':
                for f_item in cls_pairs['fail']:
                    test_cases += self.exception_pair_unit_case.format(
                        case=str(f_item).replace('[', '').replace(']', ''))
                for s_item in cls_pairs['success']:
                    test_cases += self.exception_pair_unit_case.format(
                        case=str(s_item).replace('[', '').replace(']', ''))
            elif pair_type == 'Assert':
                for f_item in cls_pairs['fail']:
                    test_cases += self.assert_pair_unit_case.format(case=str(f_item).replace('[', '').replace(']', ''))
                for s_item in cls_pairs['success']:
                    test_cases += self.assert_pair_unit_case.format(case=str(s_item).replace('[', '').replace(']', ''))
            else:
                logger.error('Not support pair type: {}', pair_type)
                raise KeyError()
        return test_cases

    def get_initial_prompt(self, buggy_code, select_pairs, repair_type="SF", bug_js={}):
        if len(select_pairs) > 0:
            test_logs = self._build_initial_test_log(select_pairs)
            if repair_type == 'SF':
                return self.pair_prompt_initial_w_pair.format(buggy_code=buggy_code, test_log=test_logs,
                                                              failing_test=bug_js['failing_tests'][0][
                                                                  'test_method_name'],
                                                              failing_line=bug_js['failing_tests'][0][
                                                                  'failing_line'].strip(),
                                                              error_message=bug_js['failing_tests'][0][
                                                                  'failure_message'].strip())
            elif repair_type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=bug_js['buggy_line'],
                    failing_test=bug_js['failing_tests'][0]['test_method_name'],
                    failing_line=bug_js['failing_tests'][0]['failing_line'].strip(),
                    error_message=bug_js['failing_tests'][0]['failure_message'].strip(),
                    test_log=test_logs)
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=bug_js['buggy_line'],
                    failing_test=bug_js['failing_tests'][0]['test_method_name'],
                    failing_line=bug_js['failing_tests'][0]['failing_line'].strip(),
                    error_message=bug_js['failing_tests'][0]['failure_message'].strip(),
                    test_log=test_logs)

        else:
            if repair_type == 'SF':
                return self.pair_prompt_initial_wo_pair.format(buggy_code=buggy_code,
                                                               failing_test=bug_js['failing_tests'][0][
                                                                   'test_method_name'],
                                                               failing_line=bug_js['failing_tests'][0][
                                                                   'failing_line'].strip(),
                                                               error_message=bug_js['failing_tests'][0][
                                                                   'failure_message'].strip())
            elif repair_type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE_WO_PAIR.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=bug_js['buggy_line'],
                    failing_test=bug_js['failing_tests'][0]['test_method_name'],
                    failing_line=bug_js['failing_tests'][0]['failing_line'].strip(),
                    error_message=bug_js['failing_tests'][0]['failure_message'].strip())
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_WO_PAIR.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=bug_js['buggy_line'],
                    failing_test=bug_js['failing_tests'][0]['test_method_name'],
                    failing_line=bug_js['failing_tests'][0]['failing_line'].strip(),
                    error_message=bug_js['failing_tests'][0]['failure_message'].strip())
        return prompt

    def get_iterative_prompt(self, buggy_func, test_pairs, message, bug_info, type='SF', infill_patch=''):
        error_message, test_method_name, failing_line, fail_line_num = message[0], message[1], message[2], message[3]
        logger.warning('test error message: {}', error_message)
        logger.warning('test method name: {}', test_method_name)
        logger.warning('test fail line: {}', failing_line)
        logger.warning('test fail line number: {}', fail_line_num)

        if error_message == "SyntaxError" or error_message == "CompileError":
            bug_prompt = "The fixed Java function has syntax and compilation errors."

        elif "[javac]" in error_message or "[exec]" in error_message:  # todo check exec
            bug_prompt = "The Java function has the following compilation error: [javac] " + ":".join(
                error_message.split(":")[1:])
        else:
            if bug_info['failing_tests'][0]['test_method_name'].strip() != test_method_name.strip() or \
                    bug_info['failing_tests'][0]['failing_line'].strip() != failing_line.strip() or \
                    bug_info['failing_tests'][0]['failure_message'].strip() != error_message.strip():
                bug_prompt = "The Java-code function has bugs on the following test method:\n`{}()`".format(
                    test_method_name.strip()) + \
                             "\non the line:\n`{}`".format(failing_line.strip()) + \
                             "\nwith the following error: {}".format(error_message.strip())
            else:
                bug_prompt = "With the repaired code provided by you, the Java-code function still has bugs on the " \
                             "following test method:\n`{}()`".format(test_method_name.strip()) + \
                             "\non the line:\n`{}`".format(failing_line.strip()) + \
                             "\nwith the following error: {}".format(
                                 error_message.strip())  # "It still does not fix the original test failure"

        if len(test_pairs) > 0:
            # test_cases = self._build_round_test_log(test_pairs)
            test_cases = self._build_initial_test_log(test_pairs)
            if type == 'SF':
                prompt = self.pair_prompt_round_w_pair.format(buggy_code=buggy_func, bugs=bug_prompt,
                                                              test_cases=test_cases)
            elif type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE.format(
                    buggy_code=(bug_info['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_info['suffix']),
                    buggy_hunk=infill_patch,
                    failing_test=test_method_name.strip(),
                    failing_line=failing_line.strip(),
                    error_message=error_message.strip(),
                    test_log=test_cases)
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE.format(
                    buggy_code=(bug_info['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_info['suffix']),
                    buggy_hunk=infill_patch,
                    failing_test=test_method_name.strip(),
                    failing_line=failing_line.strip(),
                    error_message=error_message.strip(),
                    test_log=test_cases)
        else:
            if type == 'SF':
                prompt = self.pair_prompt_round_wo_pair.format(buggy_code=buggy_func, bugs=bug_prompt)
            elif type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE_WO_PAIR.format(
                    buggy_code=(bug_info['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_info['suffix']),
                    buggy_hunk=infill_patch,
                    failing_test=test_method_name.strip(),
                    failing_line=failing_line.strip(),
                    error_message=error_message.strip())
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_WO_PAIR.format(
                    buggy_code=(bug_info['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_info['suffix']),
                    buggy_hunk=infill_patch,
                    failing_test=test_method_name.strip(),
                    failing_line=failing_line.strip(),
                    error_message=error_message.strip())
        return prompt

    # new functions for python repair process
    def get_initial_prompt4quix(self, buggy_code, select_pairs, repair_type="SF", bug_js={}):
        if len(select_pairs) > 0:
            test_logs = self._build_initial_test_log(select_pairs)
            if repair_type == 'SF':
                return self.pair_prompt_initial_w_pair_QUIX.format(buggy_code=buggy_code, error_message="Returned "
                                                                                                        "value of "
                                                                                                        "some input "
                                                                                                        "don't "
                                                                                                        "correspond "
                                                                                                        "to expected "
                                                                                                        "value.",
                                                                   test_log=test_logs)
            elif repair_type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_line=bug_js['buggy_line'],
                    error_message="Returned value of some input don't correspond to expected value.",
                    test_log=test_logs)
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=bug_js['buggy_line'],
                    error_message="Returned value of some input don't correspond to expected value.",
                    test_log=test_logs)

        else:
            if repair_type == 'SF':
                return self.pair_prompt_initial_wo_pair_QUIX.format(buggy_code=buggy_code,
                                                                    error_message="Returned value of some input don't "
                                                                                  "correspond to expected value.")
            elif repair_type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE_WO_PAIR_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_line=bug_js['buggy_line'],
                    error_message="Returned value of some input don't "
                                  "correspond to expected value.")
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_WO_PAIR_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=bug_js['buggy_line'],
                    error_message="Returned value of some input don't "
                                  "correspond to expected value.")
        return prompt

    def get_iterative_prompt4quix(self, buggy_code, select_pairs, message, bug_js={}, repair_type='SF', infill_patch=''):
        if len(select_pairs) > 0:
            test_logs = self._build_initial_test_log(select_pairs)
            if repair_type == 'SF':
                return self.pair_prompt_initial_w_pair_QUIX.format(buggy_code=buggy_code, error_message=message,
                                                                   test_log=test_logs)
            elif repair_type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_line=infill_patch,
                    error_message=message,
                    test_log=test_logs)
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=infill_patch,
                    error_message=message,
                    test_log=test_logs)

        else:
            if repair_type == 'SF':
                return self.pair_prompt_initial_wo_pair_QUIX.format(buggy_code=buggy_code,
                                                                    error_message=message)
            elif repair_type == 'SL':
                prompt = self.INIT_CHATGPT_INFILL_FAILING_TEST_LINE_WO_PAIR_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_line=infill_patch,
                    error_message=message)
            else:
                prompt = self.INIT_CHATGPT_INFILL_HUNK_FAILING_TEST_LINE_WO_PAIR_QUIX.format(
                    buggy_code=(bug_js['prefix'] + "\n" + INFILL_TOKEN + "\n" + bug_js['suffix']),
                    buggy_hunk=infill_patch,
                    error_message=message)
        return prompt
