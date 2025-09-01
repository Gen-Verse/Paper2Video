from openai import AzureOpenAI
from typing_extensions import override
from openai import AssistantEventHandler
from textblob import TextBlob
import re
import json

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

from typing import Any, Dict, List, Union

try:
    import demjson3  # pip install demjson3
except ImportError:
    demjson3 = None

try:
    import json5  # pip install json5
except ImportError:
    json5 = None

JSONType = Union[Dict[str, Any], List[Any]]

def read_pdf(pdf):
    pipeline_options = PdfPipelineOptions()
    pipeline_options.images_scale = 5.0
    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )
    raw_result = doc_converter.convert(pdf)

    raw_markdown = raw_result.document.export_to_markdown()
    text_content = re.compile(r"<!--[\s\S]*?-->").sub("", raw_markdown)
    return text_content

def classify_response(text):
    # Define keywords for affirmative and negative responses
    #affirmative_keywords = {"YES"}
    #negative_keywords = {"NO"}
    
    # Convert text to lowercase for uniform comparison

    # Check for explicit keywords
    if "NO" in text:
        return False
    
    # If no direct keywords are found, use sentiment analysis
    #sentiment_score = TextBlob(text).sentiment.polarity  # Sentiment score (-1 to 1)
    
    return True

def extract_boolean(text):
    # Check if 'YES' or 'NO' is present in the text
    if "YES" or "yes" in text:
        return True
    elif "NO" in text:
        return False
    else:
        raise ValueError("The text must contain either 'YES' or 'NO'.")
    
def text_to_list(input_text):
    pattern = r"\| (.*?) \| (.*?) \| (.*?) \|"
    matches = re.findall(pattern, input_text)
# Converting the matches to a list of dictionaries (for better structure)
    video_summary_list = [{"SCENE": match[0], "DESCRIPTION": match[1], "TIME_ALLOCATION": match[2]} for match in matches]
# Output the list
    print(video_summary_list)
    return video_summary_list

def merge_dict_keys_values(data_dict):
    if isinstance(data_dict, list):  # 如果输入是字典组成的列表
        return " ".join([" ".join([f"{key}: {value}" for key, value in data_dict.items()]) for data_dict in data_dict])
    elif isinstance(data_dict, dict):  # 如果输入是单个字典
        return " ".join([f"{key}: {value}" for key, value in data_dict.items()])
    else:
        raise TypeError("Input should be either a dictionary or a list of dictionaries.")

def read_log_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            log_content = file.read()
        return log_content
    except FileNotFoundError:
        return f"Error: The file at {file_path} was not found."
    except Exception as e:
        return f"An error occurred: {e}"
    
def filter_gemini_content(data):
    header = {'SCENE': '**SCENE**', 'DESCRIPTION': '**DESCRIPTION**', 'TIME_ALLOCATION': '**TIME_ALLOCATION**'}

    actual_content = []
    
    for entry in data:
        # 如果当前条目不是表头，则添加到实际内容列表
        if "**" in entry['DESCRIPTION']:
            pass
        else:
            actual_content.append(entry)
    
    return actual_content
    

def fix_json_string(input_str):
    input_str = input_str.replace("'", '"')  # 替换单引号为双引号
    
    input_str = re.sub(r'(?<=\w)"(?=\w)', r'\\"', input_str)  # 转义嵌套的双引号
    
    input_str = re.sub(r'\\([^\\])', r'\\\\\1', input_str)

    return input_str

def extract_dict(text):
    result_dict = {
        "scenario": "",
        "audio_content": "",
        "style": "",
        "source": "",
        "corresponding_text": "",
        "time_cost": ""
    }

    scenario_match = re.search(r'"scenario":\s*"([^"]+)"', text)
    if scenario_match:
        result_dict["scenario"] = scenario_match.group(1)

    audio_content_match = re.search(r'"audio_content":\s*"([^"]+)"', text)
    if audio_content_match:
        result_dict["audio_content"] = audio_content_match.group(1)
        
    style_match = re.search(r'"style":\s*"([^"]+)"', text)
    if style_match:
        result_dict["style"] = style_match.group(1)

    source_match = re.search(r'"source":\s*"([^"]+)"', text)
    if source_match:
        result_dict["source"] = source_match.group(1)

    corresponding_text_match = re.search(r'"corresponding_text":\s*"([^"]+)"', text)
    if corresponding_text_match:
        result_dict["corresponding_text"] = corresponding_text_match.group(1)

    time_cost_match = re.search(r'"time_cost":\s*"([^"]+)"', text)
    if time_cost_match:
        result_dict["time_cost"] = time_cost_match.group(1)

    return result_dict

def extract_list_from_text(text):
    mid_match = re.search(r'\[.*\]', text, re.DOTALL).group(0).replace('\n', '').replace('\\"', '"')
    large_matches = re.findall(r'\{[^{}]*\}', mid_match)
    scene_number = len(large_matches)
    result=[]
    for i in range(scene_number):
        result_dict = {
        "SCENE": "",
        "DESCRIPTION": "",
        "TIME_ALLOCATION": "",
        }
        current_match = large_matches[i]
        scene_match = re.search(rf'"SCENE{i+1}":\s*"([^"]+)"', current_match)
        if scene_match:
            result_dict["SCENE"] = scene_match.group(1)

        description_match = re.search(r'"DESCRIPTION":\s*"([^"]+)"', current_match)
        if description_match:
            result_dict["DESCRIPTION"] = description_match.group(1)

        time_cost_match = re.search(r'"TIME_ALLOCATION":\s*"([^"]+)"',  current_match)
        if time_cost_match:
            result_dict["TIME_ALLOCATION"] = time_cost_match.group(1)
        result.append(result_dict)
    return result

def correct_string(string):
    stripped_content = string.strip('"')

    corrected_string = '"""' + stripped_content + '"""'
    
    return corrected_string


def extract_code(input_string):
    pattern = r"(def animate\(self\):.*self.wait\(\d+\))"  # 匹配最短可能的代码块直到最后一个 self.wait(X)
    
    matches = re.findall(pattern, input_string, re.DOTALL)
    
    if matches:
        return matches[-1]  # 返回最后一个匹配项
    else:
        return input_string

def replace_animate(file_path, text):
    with open(file_path, 'r',encoding='gbk') as f:
        file_content = f.read()
    text = indent_code(text)
    new_content = re.sub(r'(def animate\(.*?\):.*?)(self.wait\(\d+\)(?:.*?self.wait\(\d+\))*)', text, file_content, flags=re.DOTALL)
    
    with open(file_path, 'w') as f:
        f.write(new_content)

def indent_code(code, indent_level=4):
    # Split code into lines
    lines = code.split('\n')
    
    # Keep the function definition line intact and indent the rest of the lines
    indented_lines = [lines[0]]  # The first line (def line) is added without change
    
    for line in lines[1:]:
        # Indent each line after the first line
        indented_lines.append(' ' * indent_level + line)
    
    return '\n'.join(indented_lines)

import regex

def first_brace_content(text: str) -> str | None:
    m = regex.search(r'\{(?:[^{}]++|(?R))*\}', text)
    return m.group(0) if m else None


# def _load_json_dict(raw: str):
#     cleaned = re.sub(r"```(?:json)?|#.*", "", raw, flags=re.I | re.M).strip()
#     cleaned = first_brace_content(cleaned)
#     try:
#         return json.loads(cleaned)
#     except json.JSONDecodeError as e:
#         return False

def _remove_comments(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"(?m)//.*?$|#.*?$", "", src)
    return src


def _sanitize_json(src: str) -> str:
    src = re.sub(r",\s*([}\]])", r"\1", src)
    src = re.sub(r"(?<!\\)'", '"', src)
    return src


def _extract_json_candidates(raw: str) -> List[str]:
    candidates = []

    # 1.  ```json ... ```
    for m in re.finditer(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw, flags=re.S | re.I):
        candidates.append(m.group(1))

    # 2.first {...}
    brace_match = re.search(r"\{.*?\}(?=\s*$|\s*[],}])", raw, flags=re.S)
    if brace_match:
        candidates.append(brace_match.group(0))

    # 3. first [...]
    brack_match = re.search(r"\[.*?\](?=\s*$|\s*[,}])", raw, flags=re.S)
    if brack_match:
        candidates.append(brack_match.group(0))

    # 4. all text
    candidates.append(raw.strip())
    return candidates

import ast
def _load_json_dict(raw: str) -> JSONType:
    """
    compatible with 3 conditions：
      1. original JSON
      2. double escaping JSON（ \\n \\u00b2）
      3. contains unescaped JSON metacharacters
    """
    # 1. extract everything from  ```json ... ``` or ``` ... ``` 
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, flags=re.I)
    body = (m.group(1) if m else raw).strip()
    
    # 2. decoding to JSON
    try:
        return json.loads(body, strict=False)
    except json.JSONDecodeError as e1:
        # 3. Handling cases with unescaped quotes
        try:
            # Use a regular expression to repair the unescaped internal quotation marks.
            fixed_body = re.sub(
                r'("[^"]*")|([^"]+)', 
                lambda m: m.group(1).replace('"', r'\"') if m.group(1) else m.group(2),
                body
            )
            return json.loads(fixed_body, strict=False)
        except json.JSONDecodeError as e2:
            #manually_fix_some bug
            try:
                # With special condition：origin "0" to origin \"0\"
                manually_fixed = body.replace('"0"', r'\"0\"')
                return json.loads(manually_fixed, strict=False)
            except json.JSONDecodeError as e3:
                raise ValueError("Unable to parse any valid JSON object/array from input.") from e3


