# ContrastARP

There are four steps to run ContrastRepair, but some of them are optional, because results(dependent files for repair) have been provided.
---------------
(optional)step1: run "main_preprocess.py" to collect original inputs and get the mutated results

(optional)step2: run "process_obj.py" to save testcases into json file

(optional)step3: For those bugs whose function input can't be mutated, run "testcase_mining" to get their original test cases, for example, "python testcase_mining.py Lang-1 True"

	  step4: modify config.py and run main.py to start repairing