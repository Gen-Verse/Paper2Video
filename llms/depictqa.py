from pathlib import Path
import requests
import logging
from typing import Optional,Union

from .base_llm import BaseLLM
from utils.custom_types import Degradation, Level


class DepictQA(BaseLLM):
    """Parameters when called: img_path_lst, task (eval_degradation or comp_quality), degradations (if task is eval_degradation)."""

    def __init__(
        self,
        log_path: Optional[Union[Path, str]] = None,
        logger: Optional[logging.Logger] = None,
        silent: bool = False,
    ):
        super().__init__(
            log_path=log_path, logger=logger, silent=silent
        )  # set attributes: cfg, logger, silent

    def query(
        self,
        img_path_lst: list[Path],
        task: str,
        degradation: Optional[Degradation] = None,
    ) -> tuple[str, str]:
        assert task in ["eval_degradation", "comp_quality"], f"Unexpected task: {task}"
        if task == "eval_degradation":
            assert (
                len(img_path_lst) == 1
            ), "Only one image should be provided for degradation evaluation."
            return self.eval_degradation(img_path_lst[0], degradation)
        else:
            assert (
                len(img_path_lst) == 2
            ), "Two images should be provided quality comparison."
            return self.compare_img_qual(img_path_lst[0], img_path_lst[1])

    def eval_degradation(
        self, img: Path, degradation: Optional[Degradation]
    ) -> tuple[str, str]:
        all_degradations: list[Degradation] = [
            "motion blur",
            "defocus blur",
            "rain",
            "haze",
            "dark",
            "noise",
            "jpeg compression artifact",
        ]
        if degradation is None:
            degradations_lst = all_degradations
        else:
            if degradation == "low resolution":
                degradation = "blur"
            else:
                assert isinstance(
                    degradation, Degradation
                ), f"Unexpected type of degradations: {type(degradation)}"
                assert (
                    degradation in all_degradations
                ), f"Unexpected degradation: {degradation}"
            degradations_lst = [degradation]

        levels: set[Level] = {"very low", "low", "medium", "high", "very high"}
        res: list[tuple[Degradation, Level]] = []
        for degradation in degradations_lst:
            prompt = depictqa_evaluate_degradation_prompt.format(
                degradation=degradation
            )
            url = "http://127.0.0.1:5001/evaluate_degradation"
            payload = {"imageA_path": img.resolve(), "prompt": prompt}
            rsp: str = requests.post(url, data=payload).json()["answer"]
            assert rsp in levels, f"Unexpected response from DepictQA: {list(rsp)}"
            res.append((degradation, rsp))

        prompt_to_display = depictqa_evaluate_degradation_prompt.format(
            degradation=degradations_lst
        )
        return prompt_to_display, str(res)

    def compare_img_qual(self, img1: Path, img2: Path) -> tuple[str, str]:
        prompt = depictqa_compare_prompt
        url = "http://127.0.0.1:5002/compare_quality"
        payload = {
            "imageA_path": img1.resolve(),
            "imageB_path": img2.resolve(),
            "prompt": prompt
        }
        rsp: str = requests.post(url, data=payload).json()["answer"]

        if "A" in rsp and "B" not in rsp:
            choice = "former"
        elif "B" in rsp and "A" not in rsp:
            choice = "latter"
        else:
            raise ValueError(f"Unexpected answer from DepictQA: {rsp}")

        return prompt, choice
