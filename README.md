# ContrastRepair
**ContrastRepair** is a LLM-based APR tool which utilizes contrastive test case pairs to enhance the repair capabilities. In general, to utilize it for program repair, there are four steps required to be executed one by one. But you can directly run any step in this repo because all the dependent files/data have already been provided.

---

### Steps to Run ContrastRepair 
- **(Optional)** Run `python main_preprocess.py` to:
  1) generate mutated test cases
  2) evaluate generated cases and retain passing ones
  3) collect original inputs for both passing and failing test cases

- **(Optional)** Run `python process_obj.py` to:
  1) parse input arguments to String type
  2) save input values of test cases into JSON file

- **(Optional)** For buggy function whose inputs cannot be mutated, run `python testcase_mining.py` to:
  1) collect their original test cases (both passing and failing ones).
  2) collect dependent functions (caller and callee)
  
  For example: 'Lang-1' is the target bug id, 'False' indicates collecting dependent functions
   ```bash
   python testcase_mining.py Lang-1 False

- **(Compulsory)** Modify the configuration file `config.py` and run `python main.py`
```python
class Config:
    openai_key: str = 'XXX'   # openai key
    result_folder: str = '/workspace/experiments/ContrastAPR'   # dir to store results
    dataset: str = 'defects4j-1.2-single-hunk'   # dataset to be repaired
    dataset_folder: str = '/workspace/ContrastAPR/data/Defects4j'   # dataset dir, where data is from data.zip
    java_tool: str = '/workspace/ContrastAPR/data/jp.jar'   # mutate tools
    repair_mode: str = 'repair'  # ['repair', 'patch_augment']
    repair_tool: str = 'single-hunk'  # ['function', 'single-hunk', 'single-line']
    total_tries: int = 40   # maximum times for restarting repair process
    repeat_num: int = 3   # maximum times for continuous repair from previous patch
    pair_type: str = 'both'  # ['no', 'exception', 'assert', 'both']
    bug_type: str = 'all'  # 'all' for all
    chatgpt_parser: str = 'complex'  # 'simple' for single-function, 'complex' for single-line and hunk
    temperature: float = 1.0   # temperature in gpt api
    pairs: int = 2   # pairs to select
