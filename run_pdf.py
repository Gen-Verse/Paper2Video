from pathlib import Path
import torch
from pipeline.preacher import Preacher
#from utils.custom_types import *
#from utils.textwork import read_log_file
import os
os.environ["CUDA_LAUNCH_BLOCKING"] = "1"

input_path = Path("dataset/example.pdf").resolve()
output_dir = Path("output").resolve()
llm_config_path=Path("config.yml").resolve()

agent = Preacher(
    input_path=input_path, output_dir=output_dir, llm_config_path=llm_config_path,
    plan_by="GEMINI",
    eval_by="GEMINI",
    art_work="GEMINI",
    with_example=True,
    with_reflection=True,
    with_rollback=True,
    silent=False,
    )

agent.run()
#high_plan=Path("output/example/logs/highplan.txt").resolve()

#high_plan=read_log_file(Path("dataset/example.log").resolve())
