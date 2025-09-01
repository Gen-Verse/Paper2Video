from pathlib import Path
import requests
import logging
from typing import Callable, Optional,Union
from time import sleep
import random
import re
from openai import AzureOpenAI
from .base_llm import BaseLLM
from typing_extensions import override
from openai import AssistantEventHandler
class GPT4_AZ(BaseLLM, AssistantEventHandler):
    """Parameters when called: img_path_lst, prompt, format_check."""

    def __init__(self,
                 config_path: Path = Path("config.yml"),
                 log_path: Optional[Union[Path, str]] = None,
                 logger: Optional[logging.Logger] = None,
                 silent: bool = False,
                 system_message: Optional[str] = None,
                 model: Optional[str] = None
                 ):
        super().__init__(
            config_path=config_path,
            log_path=log_path,
            logger=logger,
            silent=silent
        )  # set attributes: cfg, logger, silent

        self.api_key = self.cfg["GPT4_AZ"]["API_KEY"]
        if model is None:
            self.model = self.cfg["GPT4_AZ"]["MODEL"]
        else:
            self.model = model
        self.endpoint=self.cfg["GPT4_AZ"]["ENDPOINT"]
        self.version=self.cfg["GPT4_AZ"]["API_VERSION"]
        self.max_tokens = self.cfg["GPT4_AZ"]["MAX_TOKENS"]
        self.temperature = self.cfg["GPT4_AZ"]["TEMPERATURE"]
        self.prompt_tokens = 0
        self.completion_tokens = 0

        self.client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.version
        )

        self.system_message = system_message
        if self.system_message is not None:
            self._log("_Note: These user-assistant interactions are independent "
                      "and the system message is always attached in each turn for GPT._")
            self._log("**System message for GPT**")
            self._log(self.system_message)

    def query(self,
              img_path_lst: Optional[list[Path]] = None,
              pdf_path: Optional[list[Path]] = None,
              prompt: str = "",
              format_check: Optional[Callable[[object], None]] = None,
              ) -> tuple[str, str]:
        
        message = self._prepare_message_(
            prompt, img_path_lst, pdf_path)
        while True:
            response = self._send_request(message)
            self.prompt_tokens += len(prompt)
            self.completion_tokens += len(response)

            rsp_text: str = response
            if format_check is not None:
                valid, rsp_text = self._check_syntax(rsp_text, format_check)
                if not valid:
                    continue
            return prompt, rsp_text

    def _prepare_message_(self, prompt: str,
                             img_path_lst: Optional[list[Path]] = None,
                             pdf_path: Optional[list[Path]] = None,
                             ) -> list:
        content = [{
                "type": "text",
                "text": prompt
                }]
        if img_path_lst is not None:
            for img_path in img_path_lst:
                img_base64 = img_path
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": img_base64,
                        "detail": "auto"
                    }
                })

        messages = []
        #if self.system_message is not None:
            #messages.append({
                #"role": "system",
                #"content": self.system_message
            #})
        messages.append({
            "role": "user",
            "content": content
        })
        self.assistant= None

        if pdf_path is not None:
            self.assistant = self.client.beta.assistants.create(
                name="Paper to Video Assistant",
                model=self.model,
                tools=[{"type": "file_search"}],
            )

            vector_store = self.client.beta.vector_stores.create(name="Paper to Video Assistant")

            self.assistant = self.client.beta.assistants.update(
                assistant_id=self.assistant.id,
                tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
            )

            message_file = self.client.files.create(
                file=open(pdf_path, "rb"), purpose="assistants"
            )
            messages=[
                {
            "role": "user",
            "content": prompt,
      # Attach the new file to the message.
            "attachments": [
            { "file_id": message_file.id, "tools": [{"type": "file_search"}] }],} ]
            
        return  messages

    def _send_request(self, messages: list,
                      max_retries: int = 5,
                      initial_delay: int = 3,
                      exp_base: int = 2,
                      jitter: bool = True) -> requests.Response:
        """Sends a request to the OpenAI API and handles errors with exponential backoff."""

        n_retries = 0
        backoff_delay = initial_delay
        while True:
            try:
                if self.assistant != None:
                    response = self.talk_with_pdf(messages)
                else:
                    response = self.client.chat.completions.create(model=self.model, messages=messages, 
                                                        temperature=self.temperature)
            
                return response.choices[0].message.content
            except Exception as e:
                self._log("An error occurred when sending a request: "
                          f"{type(e).__name__}: {e}",
                          level='warning')
                recommended_delay = None

            n_retries += 1
            if n_retries > max_retries:
                raise RuntimeError(
                    "Too many errors occurred when querying LLM.")
            if recommended_delay is not None:
                delay = recommended_delay
            else:
                backoff_delay *= exp_base * (1 + jitter*random.random())
                delay = backoff_delay
            self._log(
                f"Retrying in {delay:.3f} seconds...", level='warning')
            sleep(delay)

    def _check_response(self, response: requests.Response) -> tuple[bool, Optional[float]]:
        """Checks if the response is valid. If error occurs, gets the recommended delay if any.

        Args:
            response (requests.Response): Response from the OpenAI API to check.

        Returns:
            is_valid (bool): Whether the response is valid.
            recommended_delay (float | None): The delay recommended by the API if any.
        """

        if "error" in response.json():
            err_msg: str = response.json()['error']['message']
            self._log(f"An error occurred when querying LLM: {err_msg}",
                      level='warning')

            recommended_delay = None
            if response.json()['error']['code'] == 'rate_limit_exceeded':
                # there may exist "Please try again in xxs/xxmxxs/xxms." in the error message
                match = re.search(
                    R"(?<=Please try again in )(\d+m)?\d+\.?\d*(?=s)", err_msg)
                if match is not None:
                    t = match.group().split('m')
                    m = t[0] if len(t) > 1 else 0
                    s = t[-1]
                    recommended_delay = 60*int(m) + float(s)

            return False, recommended_delay

        if (finish_reason := response.json()['choices'][0]['finish_reason']) != 'stop':
            self._log(f"finish_reason if {finish_reason}", level='warning')

        return True, None

    def _check_syntax(self, rsp_text: str, format_check: Callable[[object], None]
                      ) -> tuple[bool, str]:
        """Checks whether the response is a valid Python object and follows the specified format. 
        If valid, returns the processed response (the valid response may be wrapped in something)."""
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
                self._log("Failed to parse the response:", level='warning')
                self._log(rsp_text, level='warning')
                return False, ""
        # Check if the response follows the specified format
        try:
            format_check(obj)
        except AssertionError as e:
            self._log(f"Failed to pass the format check: {e}", level='warning')
            self._log(f"Response: {obj}", level='warning')
            return False, ""
        return True, rsp_text
    
    def _post_process(self):
        """Logs the token usage and cost."""        
        self._log("Token usage so far: "
                  f"{self.prompt_tokens} prompt tokens, "
                  f"{self.completion_tokens} completion tokens")
        total_cost = self.prompt_tokens/1000*0.01 + self.completion_tokens/1000*0.03
        self._log(f"Cost so far: ${total_cost:.5f}")

    def talk_with_pdf(self, messages):
        print(1)
        thread = self.client.beta.threads.create(
            messages=messages)
        with self.client.beta.threads.runs.stream(
            thread_id=thread.id,
            assistant_id=self.assistant.id,
            instructions="",
            event_handler=EventHandler(self.client),
        ) as stream:
            stream.until_done()
        return final_response


class EventHandler(AssistantEventHandler):
    def __init__(self, client):
        super().__init__()
        self.client = client

    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)
    @override
    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)
    @override
    def on_message_done(self, message) -> None:
        # print a citation to the file searched
        message_content = message.content[0].text
        annotations = message_content.annotations
        citations = []
        for index, annotation in enumerate(annotations):
            message_content.value = message_content.value.replace(
                annotation.text, f"[{index}]"
            )
            if file_citation := getattr(annotation, "file_citation", None):
                cited_file = self.client.files.retrieve(file_citation.file_id)
                citations.append(f"[{index}] {cited_file.filename}")
        global final_response
        final_response = message_content.value