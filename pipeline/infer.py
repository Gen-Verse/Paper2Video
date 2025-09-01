from pathlib import Path

from .preacher import IRAgent
from utils.custom_types import *


input_path = Path("dataset/greengard.pdf").resolve()
output_dir = Path("output").resolve()

agent = IRAgent(
    input_path=input_path, output_dir=output_dir,
    evaluate_degradation_by="depictqa",
    with_retrieval=True,
    with_reflection=True,
    reflect_by="depictqa",
    with_rollback=True,
    silent=False
    )

agent.run()
