from pathlib import Path
import logging
from typing import Optional,Union
import yaml
from utils.textwork import correct_string
from utils.misc import encode_img
from utils.logger import get_logger


class BaseLLM:
    def __init__(self,
                 config_path: Optional[Path] = None,
                 log_path: Optional[Path] = None,
                 logger: Optional[logging.Logger] = None,
                 silent: bool = False
                 ):
        if config_path is not None:
            with open(config_path, "r") as f:
                self.cfg: dict = yaml.safe_load(f)
        else:
            self.cfg = None

        self.silent = silent

        self.logger = None
        if logger is not None:
            assert log_path is None, "log_path should be None when logger is provided."
            self.logger = logger
        elif log_path is not None:
            self.logger = get_logger(
                logger_name=self.__class__.__name__,
                log_file=log_path,
                console_log_level=logging.WARNING,
                file_format_str="%(message)s",
                silent=self.silent)

    def query(self,
              img_path_lst: Optional[list[Path]] = None,
              *args, **kwargs) -> tuple[str, str]:
        """Returns the prompt and response in text."""
        raise NotImplementedError

    def __call__(self,
                 img_path: Optional[Union[Path, list[Path]]] = None,
                 *args, **kwargs) -> str:
        """Queries the model and logs the chat."""
        img_path_lst = img_path
        if img_path is not None:
            if isinstance(img_path, Path):
                img_path_lst = [img_path]
            else:
                assert isinstance(img_path, list), \
                    f"Unexpected type of img_path: {type(img_path)}"
        prompt, rsp_text = self.query(img_path_lst, *args, **kwargs)
        rsp_text = correct_string(rsp_text)
        img_base64_lst = []
        if img_path_lst is not None:
            for img_path in img_path_lst:
                img_base64 = img_path
                img_base64_lst.append(img_base64)

        self._log_chat(prompt, img_base64_lst, rsp_text)
        self._post_process()

        return rsp_text

    def _post_process(self):
        pass

    def _log_chat(self,
                  prompt: str,
                  img_base64_lst: list[str],
                  rsp_text: str) -> None:
        """Logs the single-round chat in markdown format."""
        def escape(s: str):
            return s.replace('<', R'\<').replace('>', R'\>')
        self._log("**Question**")
        self._log(f"{escape(prompt)}")
        if img_base64_lst is not None:
            for img_base64 in img_base64_lst:
                self._log(f"![image]({img_base64})")
        self._log(f"**Answer (from {self.__class__.__name__})**")
        self._log(f"{escape(rsp_text)}")

    def _log(self, message: str, level: str = 'info') -> None:
        """Adds another line break to improve readability in markdown."""
        if self.logger is not None:
            log_fn = eval(f'self.logger.{level}')
            log_fn(message + '\n')
        if level != 'info' and (self.logger is None or self.silent):
            print(message)
