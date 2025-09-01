# This script calls Llama API provided by https://www.llama-api.com/

from pathlib import Path
import requests
import logging
from typing import Callable, Optional
from time import sleep
import random

from .base_llm import BaseLLM
from llamaapi import LlamaAPI


class Llama(BaseLLM):

    def __init__(
        self,
        config_path: Path = Path("config.yml"),
        log_path: Optional[Path | str] = None,
        logger: Optional[logging.Logger] = None,
        silent: bool = False,
        system_message: Optional[str] = None,
        model: Optional[str] = None,
    ):
        super().__init__(
            config_path=config_path, log_path=log_path, logger=logger, silent=silent
        )  # set attributes: cfg, logger, silent

        self.api_key = self.cfg["LLAMA"]["API_KEY"]
        if model is None:
            self.model = self.cfg["LLAMA"]["MODEL"]
        else:
            self.model = model
        self.max_tokens = self.cfg["LLAMA"]["MAX_TOKENS"]
        self.temperature = self.cfg["LLAMA"]["TEMPERATURE"]
        
        self.llama = LlamaAPI(self.api_key)

        self.prompt_tokens = 0
        self.completion_tokens = 0

        self.system_message = system_message
        if self.system_message is not None:
            self._log(
                "_Note: These user-assistant interactions are independent "
                "and the system message is always attached in each turn for Llama._"
            )
            self._log("**System message for Llama**")
            self._log(self.system_message)

    def query(
        self,
        img_path_lst: Optional[list[Path]] = None,
        prompt: str = "",
        format_check: Optional[Callable[[object], None]] = None,
    ) -> tuple[str, str]:
        payload = self._prepare_for_request(prompt)
        max_retries = 5
        n_retries = 0
        while True:
            response = self._send_request(payload)

            usage = response.json()["usage"]
            self.prompt_tokens += usage["prompt_tokens"]
            self.completion_tokens += usage["completion_tokens"]

            rsp_text: str = response.json()["choices"][0]["message"]["content"]
            if format_check is not None:
                valid, rsp_text = self._check_syntax(rsp_text, format_check)
                if not valid:
                    n_retries += 1
                    if n_retries > max_retries:
                        raise RuntimeError("Too many errors occurred when parsing the response.")
                    continue
            return prompt, rsp_text
        
    def _prepare_for_request(self, prompt: str) -> dict:
        messages = [{"role": "user", "content": prompt}]
        if self.system_message is not None:
            messages.insert(0, {"role": "system", "content": self.system_message})
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }
        return payload

    def _send_request(
        self,
        payload: dict,
        max_retries: int = 5,
        initial_delay: int = 3,
        exp_base: int = 2,
        jitter: bool = True,
    ) -> requests.Response:
        """Sends a request to the OpenAI API and handles errors with exponential backoff."""

        n_retries = 0
        backoff_delay = initial_delay
        while True:
            try:
                response = self.llama.run(payload)
                if (finish_reason := response.json()["choices"][0]["finish_reason"]) != "stop":
                    self._log(f"finish_reason is {finish_reason}", level="warning")
                return response
            except Exception as e:
                self._log(
                    "An error occurred when sending a request: "
                    f"{type(e).__name__}: {e}",
                    level="warning",
                )

            n_retries += 1
            if n_retries > max_retries:
                raise RuntimeError("Too many errors occurred when querying LLM.")
            backoff_delay *= exp_base * (1 + jitter * random.random())
            delay = backoff_delay
            self._log(f"Retrying in {delay:.3f} seconds...", level="warning")
            sleep(delay)

    def _check_syntax(
        self, rsp_text: str, format_check: Callable[[object], None]
    ) -> tuple[bool, str]:
        """Checks whether the response is a valid Python object and follows the specified format.
        If valid, returns the processed response (the valid response may be wrapped in something).
        """
        # Check if the response is a valid Python object
        try:
            obj = eval(rsp_text)
        except:
            # GPT may wrap the response in a code block
            inner_rsp_text = rsp_text.strip("```").lstrip("json").strip()
            try:
                obj = eval(inner_rsp_text)
                rsp_text = inner_rsp_text
            except:
                self._log("Failed to parse the response:", level="warning")
                self._log(rsp_text, level="warning")
                return False, ""
        # Check if the response follows the specified format
        try:
            format_check(obj)
        except AssertionError as e:
            self._log(f"Failed to pass the format check: {e}", level="warning")
            self._log(f"Response: {obj}", level="warning")
            return False, ""
        return True, rsp_text

    def _post_process(self):
        """Logs the token usage and cost."""
        self._log(
            "Token usage so far: "
            f"{self.prompt_tokens} prompt tokens, "
            f"{self.completion_tokens} completion tokens"
        )
