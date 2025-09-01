from transformers import Qwen2_5_VLForConditionalGeneration, AutoTokenizer, AutoProcessor, BitsAndBytesConfig
from qwen_vl_utils import process_vision_info
from .base_llm import BaseLLM
from typing import Callable, Optional,Union
from pathlib import Path
from utils.textwork import read_pdf
import logging
import torch


class QWEN(BaseLLM):
    """Parameters when called: img_path_lst, prompt, format_check."""
    def __init__(self,
                 config_path: Path = Path("config.yml"),
                 log_path: Optional[Union[Path, str]] = None,
                 logger: Optional[logging.Logger] = None,
                 silent: bool = False,
                 system_message: Optional[str] = None,
                 model: Optional[str] = None
                 ):
        super().__init__(config_path=config_path,
            log_path=log_path,
            logger=logger,
            silent=silent)  # set attributes: cfg, logger, silent

        self.dir = self.cfg["QWEN"]["local_dir"]
        self.prompt_tokens = 0
        self.completion_tokens = 0

        self.system_message = system_message
        if self.system_message is not None:
            self._log("_Note: These user-assistant interactions are independent "
                      "and the system message is always attached in each turn for GPT._")
            self._log("**System message for GPT**")
            self._log(self.system_message)
        bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True, bnb_4bit_quant_type='nf4')
        self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            self.dir, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, quantization_config=bnb_config)#, attn_implementation="flash_attention_2"
        self.processor = AutoProcessor.from_pretrained(self.dir)    
    def _prepare_message_(self, prompt: str,
                             img_path_lst: Optional[list[Path]] = None,
                             pdf_path: Optional[list[Path]] = None,
                             ) -> list:
        content = []
        
        if img_path_lst is not None:
            for img_base64 in img_path_lst:
                #img_base64 = img_path
                content.append(
                {"type": "image", "image": img_base64})
        if pdf_path is not None:
            doc_data = read_pdf(pdf_path)
            content.append(
                {'type': 'text', 'text': prompt+doc_data})
        else:
            content.append({'type': 'text', 'text': prompt})
            
        return  content
    def query(self,
              img_path_lst: Optional[list[Path]] = None,
              pdf_path: Optional[list[Path]] = None,
              prompt: str = "",
              format_check: Optional[Callable[[object], None]] = None,
              ) -> tuple[str, str]:

        messages = self._prepare_message_(
            prompt, img_path_lst, pdf_path)
        while True:
            text = messages[0]['text'] 
            image_inputs, video_inputs=None, None
            if img_path_lst is not None:
                text=self.processor.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )       
                image_inputs, video_inputs = process_vision_info(messages)
            inputs = self.processor(
                text=[text],
                images=image_inputs,
                videos=video_inputs,
                padding=True,
                return_tensors="pt",
            )
            inputs = inputs.to("cuda")

# Inference: Generation of the output
            generated_ids = self.model.generate(**inputs, max_new_tokens=128)
            generated_ids_trimmed = [
                out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
            ]
            output_text = self.processor.batch_decode(
                generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
            )[0]
            return prompt, output_text   
