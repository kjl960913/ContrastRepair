# ContrastRepair

There are four steps to run **ContrastRepair**, but some of them are optional because the results (dependent files for repair) have already been provided.

---

### Steps to Run ContrastRepair

1. **(Optional)** Run `main_preprocess.py` to collect original inputs and generate the mutated results.

2. **(Optional)** Run `process_obj.py` to save test cases into a JSON file.

3. **(Optional)** For bugs whose function inputs cannot be mutated, run `testcase_mining.py` to retrieve their original test cases. For example:
   ```bash
   python testcase_mining.py Lang-1 True
