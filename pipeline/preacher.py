from pathlib import Path
from PIL import Image
import logging
from time import localtime, strftime
import json
import random
from typing import Optional
import re
import os 
from llms import GPT4, DepictQA, GPT4_AZ, GEMINI,QWEN
from . import prompts
from utils.slides import create_ppt_style_image, get_specific_element
from utils.logger import get_logger
from utils.custom_types import *
from utils.textwork import merge_dict_keys_values, classify_response, text_to_list, extract_code,replace_animate,extract_dict,extract_list_from_text, _load_json_dict
from utils.videowork import extract_key_frames, merge_video_audio, image_to_images, image_to_video, concatenate_videos
from utils.math_vis import render_video
from moviepy.editor import VideoFileClip
from tools import Wanxiang_video, Wanxiang_image, TavusClient, Qwentts
from utils.misc import download_file, name_to_pdb_ids, download_pdb
from utils.mol import generate_mol_animation

class Preacher:
    """
    Args:
        input_path (Path): Path to the input image.
        output_dir (Path): Path to the output directory, in which a directory will be created.
        llm_config_path (Path, optional): Path to the config file of LLM. Defaults to Path("config.yml").
        plan_by (str, optional): The method of degradation evaluation, "depictqa" or "gpt4v". Defaults to "depictqa".
        with_retrieval (bool, optional): Whether to schedule with retrieval. Defaults to True.
        schedule_example_path (Path | None, optional): Path to the example hub. Defaults to Path( "memory/schedule_example.json").
        with_reflection (bool, optional): Whether to reflect on the results of tools. Defaults to True.
        eval_by (str, optional): The method of reflection on results of tools, "depictqa" or "gpt4v". Defaults to "depictqa".
        with_rollback (bool, optional): Whether to roll back when failing in one subtask. Defaults to True.
        silent (bool, optional): Whether to suppress the console output. Defaults to False.
    """

    def __init__(
        self,
        input_path: Path,
        output_dir: Path,
        llm_config_path: Path ,
        plan_by: str,
        eval_by: str,
        art_work: str,
        with_example: bool = True,
        schedule_example_path: Optional[Path] = Path(
            "memory/schedule_example.json"
        ),
        with_reflection: bool = True,
        with_rollback: bool = True,
        silent: bool = False,
        max_high_plan_iteration: int = 15,
        max_low_plan_iteration: int = 30,
        max_generate_iteration: int = 10,
        general_video_work: str = "wanx",
        talking_head_work: str = "Tavus",
        captioning_work: str = "wanx",
        slides_work: str = "xinghuo",
        audio_work: str = "qwentts",
    ) -> None:
        # paths
        self.pdf_path = input_path
        self.low_plan_order = ["style","audio_content","source","prompt"]
        self._prepare_dir(input_path, output_dir)
        # config
        self._config(
            plan_by,
            with_example,
            with_reflection,
            eval_by,
            with_rollback,
            max_high_plan_iteration,
            max_low_plan_iteration,
            max_generate_iteration,
            art_work,
            general_video_work,
            talking_head_work,
            captioning_work,
            slides_work,
            audio_work,
        )
        # components
        self._create_components(llm_config_path, schedule_example_path, silent)
        # constants
        self._set_constants()

    def _config(
        self,
        plan_by: str,
        with_example: bool,
        with_reflection: bool,
        eval_by: str,
        with_rollback: bool,
        max_low_plan_iteration:int,
        max_high_plan_iteration:int,
        max_generate_iteration:int,
        art_work: str,
        general_video_tool: str ,
        talking_head_tool: str,
        captioning_tool: str  ,
        slides_tool: str ,
        audio_tool: str ,
    ) -> None:
        #assert plan_by in {"GPT4v", "depictqa", "GPT4_AZ", "GEMINI"}
        self.plan_by = plan_by
        self.with_example = with_example
        
        self.eval_by = eval_by
        #assert eval_by in {"GPT4v", "depictqa", "GPT4_AZ", "GEMINI"}
        self.art_work = art_work
        self.with_reflection = with_reflection
        
        self.with_rollback = with_rollback
        self.max_high_plan_iteration=max_high_plan_iteration
        self.max_low_plan_iteration=max_low_plan_iteration
        
        self.general_video_tool = general_video_tool
        self.talking_head_tool= talking_head_tool
        self.captioning_tool= captioning_tool
        self.slides_tool = slides_tool
        self.audio_tool = audio_tool
        self.max_generate_iteration =max_generate_iteration

    def _create_components(
        self,
        llm_config_path: Path,
        schedule_example_path: Optional[Path],
        silent: bool,
    ) -> None:
        # logger
        self.qa_logger = get_logger(
            logger_name="QA",
            log_file=self.qa_path,
            console_log_level=logging.WARNING,
            file_format_str="%(message)s",
            silent=silent,
        )
        workflow_format_str = "%(asctime)s - %(levelname)s\n%(message)s\n"
        self.workflow_logger: logging.Logger = get_logger(
            logger_name="Workflow",
            log_file=self.workflow_path,
            console_format_str=workflow_format_str,
            file_format_str=workflow_format_str,
            silent=silent,
        )

        # LLM
        if self.plan_by == "GPT4v":
            self.planner = GPT4(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.plan_by == "depictqa" or self.eval_by == "depictqa":
            self.planner = DepictQA(logger=self.qa_logger, silent=silent)
        elif self.plan_by == "GPT4_AZ":
            self.planner = GPT4_AZ(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.plan_by == "GEMINI":
            self.planner = GEMINI(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.plan_by == "QWEN":
            self.planner = QWEN(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        
        # LLM evaluator
        if self.eval_by == "GPT4v":
            self.evaluator = GPT4(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.eval_by == "depictqa" :
            self.evaluator = DepictQA(logger=self.qa_logger, silent=silent)
        elif self.eval_by== "GPT4_AZ":
            self.evaluator = GPT4_AZ(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.eval_by == "GEMINI":
            self.evaluator = GEMINI(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.eval_by == "QWEN":
            self.evaluator = QWEN(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        #Generator
        if self.art_work == "GPT4_AZ":
            self.art_agent = GPT4_AZ(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.art_work == "GEMINI":
            self.art_agent = GEMINI(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        elif self.art_work == "QWEN":
            self.art_agent = QWEN(
                config_path=llm_config_path,
                logger=self.qa_logger,
                silent=silent,
                system_message=prompts.system_message,
            )
        if self.audio_tool== "qwentts":
            self.audio_tool = Qwentts(config_path=llm_config_path)
        if self.general_video_tool == "wanx":
            self.general_video_tool = Wanxiang_video(config_path=llm_config_path)
        if self.captioning_tool == "wanx":
            self.captioning_tool = Wanxiang_image(config_path=llm_config_path)
        self.talking_head_tool = TavusClient(config_path=llm_config_path)
        # example
        if self.with_example:
            assert (
                schedule_example_path is not None
            ), "Example should be provided."
            with open(schedule_example_path, "r") as f:
                examples = json.load(f)
            self.high_example = examples["high_examples"]
            self.low_example = examples["low_examples"]
            self.manim_example = examples["MANIM_examples"]
        random.seed(0)

    def _set_constants(self) -> None:
        self.degra_subtask_dict: dict[Degradation, Subtask] = {
            "low resolution": "super-resolution",
            "noise": "denoising",
            "motion blur": "motion deblurring",
            "defocus blur": "defocus deblurring",
            "haze": "dehazing",
            "rain": "deraining",
            "dark": "brightening",
            "jpeg compression artifact": "jpeg compression artifact removal",
        }
        self.subtask_degra_dict: dict[Subtask, Degradation] = {
            v: k for k, v in self.degra_subtask_dict.items()
        }
        self.degradations = set(self.degra_subtask_dict.keys())
        self.subtasks = set(self.degra_subtask_dict.values())
        self.levels: list[Level] = ["very low", "low", "medium", "high", "very high"]
        
    def _ensure_audio(self, content: str, return_url=False) -> Path:
        target = self.curr_scene_dir / "audio.wav"
        if target.exists():
            return target
        url = self.audio_tool.return_audio(content)
        if return_url:
            return url 
        return Path(download_file(url, target)) 
    def run(self, high_plan: Optional[list[Subtask]]=None) -> None:#low_plan: Optional[list[Subtask]]=None, cache: Optional[Path]=None
        if high_plan is not None:
            with open(high_plan, 'r') as file:
                self.high_plan = file.read() 
        else:
            self.high_plan=self.high_planning()
        self.high_plan_list = extract_list_from_text(self.high_plan)
        # if self.plan_by=='GEMINI':
        #     self.high_plan_list = filter_gemini_content(self.high_plan_list)
        self.final_plan=[]
        for i in range(len(self.high_plan_list)):#len(self.high_plan_list)
            self.final_plan.append({"scenario": "",
                                    "time_cost": "",
                                    "audio_content": "",
                                    "style": "",
                                    "source": "",
                                    "prompt": ""
                                    })
            self.scene_idx = i
            self.low_planning(self.high_plan_list[i])#self.high_plan_list[i]
        self.video_list = []
        for i in range(len(self.high_plan_list)):#len(self.high_plan_list)
            self.scene_idx = i
            self.generate_(i)
            self.video_list.append(self.work_dir /f"scene_{self.scene_idx}"/"scene{}.mp4".format(self.scene_idx))#self.generate_(i)) 
        concatenate_videos(self.video_list, self.final_video_path_)

    def high_planning(self) -> None:
        """Sets the initial plan."""
        if os.path.exists(self.high_plan_path):
            with open(self.high_plan_path, "r") as file:
                high_plan_legal = file.read()
                return high_plan_legal
        if self.with_reflection:
            high_planning_success=False
            iter=0
            eval_results=None
            high_plan=None
            while high_planning_success == False and (iter < self.max_high_plan_iteration):
                high_plan = self.high_plan_by_llm(eval_results, high_plan)
                high_plan_legal = self.setting_plan_format(high_plan,step="high")
                high_planning_success, eval_results = self.high_evaluate_by_llm(high_plan_legal)
                iter += 1
        else:
            high_plan = self.high_plan_by_llm()
            
        self.workflow_logger.info(f"High Level Plan: {high_plan_legal}")
        # with open(self.high_plan_path, 'w') as file:
        #     file.write(high_plan_legal)
        with open(self.high_plan_path, 'w', encoding='utf-8') as f:
            json.dump(high_plan_legal, f, ensure_ascii=False, indent=2)
        return high_plan_legal
    
    def high_plan_by_llm(self,eval_results, high_plan) -> str:
        if eval_results:
            prompt = high_plan + ' \n '+ prompts.high_level_replanning_prompt + eval_results
        else:
            prompt = prompts.high_level_planning_prompt
            if self.with_example :
                prompt += ' \n '+ merge_dict_keys_values(self.high_example) 
        high_plan = eval(
            self.planner(
                prompt=prompt,
                pdf_path=Path(self.pdf_path),
            )
        )
        self.workflow_logger.info(f"High_plan: {high_plan}")
        return  high_plan
    
    def high_evaluate_by_llm(self, high_plan) -> str:
        prompt = prompts.high_level_evaluate_prompt + ' \n '+ high_plan
        eval_results = eval(
            self.evaluator(
                prompt = prompt,
                pdf_path=Path(self.pdf_path),
                ))
        success = classify_response(eval_results)
        self.workflow_logger.info(f"Eval_Results: {eval_results}")
        return success, eval_results
    
    def low_planning(self, part_plan):
        plan_file = self.log_dir/f"file_{self.scene_idx}.json"
        self.final_plan[self.scene_idx]['scenario'] = part_plan['SCENE']
        self.final_plan[self.scene_idx]['time_cost'] = part_plan['TIME_ALLOCATION']
        if os.path.exists(plan_file):
            with open(plan_file, "r") as file:
                self.final_plan[self.scene_idx] = json.load(file)
                return None
        elif self.with_reflection:
            iter=0
            eval_results=None
            low_plan=None
            low_plan_legal=None
            plan_idx=2
            while plan_idx < 6 and iter < self.max_low_plan_iteration:
                low_plan = self.low_plan_by_llm(part_plan, eval_results, low_plan_legal)
                low_plan_legal = self.setting_plan_format(low_plan)
                plan_idx, eval_results = self.low_evaluate_by_llm(plan_idx, low_plan_legal)
                iter += 1
        else:
            low_plan = self.low_plan_by_llm()
            low_plan_legal = self.setting_plan_format(low_plan)
            self.final_plan[self.scene_idx] = extract_dict(low_plan_legal)
        

        with open(plan_file, "w") as file:
            json.dump(self.final_plan[self.scene_idx], file)
    
    def low_plan_by_llm(self, part_plan, eval_results, low_plan_legal) -> str:
        if eval_results:
            prompt = low_plan_legal + ' \n '+ prompts.low_level_replanning_prompt + eval_results
        else:
            prompt = merge_dict_keys_values(prompts.low_level_planning_prompt) + merge_dict_keys_values(part_plan)
            if self.with_example :
                prompt += 'Here are some examples, not the scene I want to ask you:'+ ' \n '+ merge_dict_keys_values(self.low_example) 
        low_plan = eval(
            self.planner(
                prompt=prompt,
                pdf_path=Path(self.pdf_path),
            )
        )
        #self.workflow_logger.info(f"low_plan: {low_plan}")
        return  low_plan
    
    def low_evaluate_by_llm(self, plan_idx, low_plan_legal):
        while plan_idx < 6:
            current_sec = self.low_plan_order[plan_idx-2]
            pattern = rf'"{current_sec}":\s*(?:"([^"]*)"|(\{{.*?\}})|(\[.*?\]))'
            match = re.search(pattern, low_plan_legal, re.DOTALL)
            if match:
                self.final_plan[self.scene_idx][current_sec] = match.group(1) if match.group(1) else match.group(2) if match.group(2) else match.group(3)       

            prompt = prompts.low_level_evaluate_prompt +  prompts.low_level_evaluate_prompt_list[plan_idx-2] + str(self.final_plan[self.scene_idx])
            eval_results = eval(
                self.evaluator(
                    prompt = prompt,
                    pdf_path=Path(self.pdf_path),
                    ))
            success = classify_response(eval_results)
            self.workflow_logger.info(f"Eval_Results: {eval_results}")
            if not success:
                return plan_idx, eval_results
            if success: 
                plan_idx += 1
        return plan_idx, eval_results
    
    def generate_(self, scene_idx):
        self.curr_scene_dir = self.work_dir / "scene_{}".format(scene_idx)
        if not os.path.isdir(self.curr_scene_dir):
            self.curr_scene_dir.mkdir()
        style = self.final_plan[scene_idx]["style"].lower()
        if "general" in style.lower() :
            video_path=self.general_work(scene_idx)
        elif "prof" in style.lower() or "scie" in style.lower() or "math" in style.lower() or "mol" in style.lower():
            video_path=self.professional_work(scene_idx)
        elif "cap" in style.lower():
            video_path=self.captioning_work(scene_idx)
        elif "slides" in style.lower():
            video_path=self.slides_work(scene_idx)
        elif "heads" in style.lower() :
            video_path=self.talking_head_work(scene_idx)
        else: print("error: Please check the style file")
        return video_path

    def math_single_work(self, plan, eval_results=None, code_str=None):
        eval_prompt = "Please check if the above code follows the rules mentioned. If not, modify it: "+\
            "The first line should be 'def animate(self):\n'; the last line should be in the format 'self.wait(X)', where X is a positive integer;"+\
                " does the code have a strong mathematical nature? Does it align with theme {}? Directly output the modified code (Code should be easy). Error message:".format(plan["prompt"])
        if eval_results==None:
            prompt = " Please write a python function named animate at the letf-bottom part in the bottom left corner of the screen about {}. ".format(plan["source"])+\
                "The requirements are: "+\
                "Use the MANIM package function should be part of the Scene class in MANIM , NO NEED TO IMPORT package"+\
                "The first line SHOULD be 'def animate(self):\n '; the last line should be in the format 'self.wait(X)'"+\
                " The function product visual content such as intuitive function graphs."+\
                " Should conform to {} and {}.".format(plan["source"], plan["prompt"]) +\
                " Only output the function defnition code. Example:"
            prompt_r = "Rewrite this promptso as A WHOLE sentence to make it fits as acaption in a video. Keep the word with around 5 words perline"+\
                " using \"\n\" to separate lines. JUST A MEANINGFUL sentence!"
            plan["prompt"] = eval(
                self.art_agent(
                    prompt=prompt_r+"\n" + plan["prompt"],
                ))
            code_str = eval(
                self.art_agent(
                    prompt=prompt+self.manim_example,
                    pdf_path=Path(self.pdf_path),
                    ))
        else:
            code_str = eval(
                self.art_agent(
                    prompt=  eval_results+ "\n"+code_str,
                    pdf_path=Path(self.pdf_path),
                    ))
        code_str = eval(
                self.art_agent(
                    prompt=prompts.pro_format_prompt+"\n" + code_str,
                    ))
        code_str = extract_code(code_str)
        video_path = None
        while video_path == None:
            try:
                replace_animate(self.animate_path, code_str)
                video_path = render_video(self.curr_scene_dir,plan)
            except Exception as e:
                code_str = eval(
                self.evaluator(
                    prompt= code_str+ "\n"+ eval_prompt,
                ))
                code_str = eval(
                    self.evaluator(
                prompt=prompts.pro_format_prompt+"\n" + code_str,
                ))
                code_str = extract_code(code_str)
        return code_str, video_path
    
    def professional_work(self, scene_idx):
        video_success = False
        iter=0
        plan = self.final_plan[scene_idx]
        code_str = None
        eval_results = None
        
        self.curr_video_path = self.curr_scene_dir/"video.mp4"
        
        style_ = eval(
            self.evaluator(prompt=prompts.pro_classify_prompt+plan["prompt"],))
        if "math" in style_.lower():
            if os.path.exists(self.curr_video_path):
                  pass
            else:
                while video_success == False and iter < self.max_generate_iteration:
                    code_str, video_path = self.math_single_work(plan,eval_results,code_str)
                    video_success, eval_results = self.video_evaluate_by_mllm(plan, video_path, type='video')
                    iter += 1
                video = VideoFileClip(video_path)
                video.write_videofile(self.curr_video_path)
        elif "mol" in style_.lower():
            if os.path.exists(self.curr_video_path):
                pass
            else:
                
                prompt_mol = f"Please return the most related name  'X' of the protein in {plan["source"]} and {plan["prompt"]}. Keep it concise and breif."+" Return the name ONLY"
                
                pdb_name = eval(
                    self.evaluator(
                    prompt=prompt_mol,))
                audio_mol = f'Optimize the {plan["audio_content"]} to transform it into an introduction related to molecular biology, mentioning the protein {pdb_name}, without exceeding 50 words. Return the UPDATED prompt ONLY'
                self.final_plan[scene_idx]["audio_content"] = eval(
                    self.evaluator(
                    prompt=audio_mol,))
                #pdb_name = _load_json_dict(pdb_name)['name']
                ids = name_to_pdb_ids(pdb_name)
                if not ids:
                    print("[MANUAL] no PDB ID, please check:", pdb_name)
                    return
                pdb_id=ids[0]
                pdb_path = os.path.join(self.curr_scene_dir, f"{pdb_id.lower()}.pdb")
                if not os.path.exists(pdb_path):
                    download_pdb(pdb_id, pdb_path)
                if pdb_path:
                    print(f"[DONE] {pdb_id} is saved at  {pdb_path}")
                    generate_mol_animation(pdb_path, self.curr_video_path)
                else:
                    url = f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb"
                    print(f"[MANUAL] please download and generate by yourself:{url}")
                    
                #video = VideoFileClip(self.curr_video_path)
                #video.write_videofile(self.curr_video_path)
        self.curr_audio_path = self._ensure_audio(self.final_plan[scene_idx]["audio_content"])
        self.final_video_path = self.curr_scene_dir/"scene{}.mp4".format(scene_idx)
        if "time_cost" in plan:
            time = plan["time_cost"]
        else:
            time = '8'
        merge_video_audio(self.curr_video_path, self.curr_audio_path, time,self.final_video_path)
        return self.final_video_path

    def general_single_work(self, plan, eval_results=None):
        if eval_results==None:
            prompt_r = " Please use {} as the materials to depict a video scene that a diffusion model can understand and generate.".format( plan["prompt"])
            plan["prompt"] = eval(
            self.art_agent(
                    prompt=prompt_r+ "\n" + plan["prompt"],
            ))
        else:
            plan["prompt"] = eval(
            self.art_agent(
                    prompt=eval_results + "\n" + plan["prompt"],
            ))
        video_url = self.general_video_tool.query(plan["prompt"])
        return video_url
    
    def general_work(self, scene_idx):
        video_success = False
        iter=0
        plan = self.final_plan[scene_idx]
        eval_results = None
        self.final_video_path = self.curr_scene_dir/"scene{}.mp4".format(scene_idx)
        self.curr_video_path = self.curr_scene_dir/"video.mp4".format(scene_idx)
        self.curr_audio_path = self._ensure_audio(plan["audio_content"])
        if os.path.exists(self.curr_video_path):
            video_path=self.curr_video_path
            pass
        else:
            while video_success == False and iter < self.max_generate_iteration:
                video_path = self.curr_scene_dir/"test{}.mp4".format(iter)
                if not os.path.exists(video_path):
                    video_url = self.general_single_work(plan, eval_results)
                    video_path = download_file(video_url, video_path)
                video_success, eval_results = self.video_evaluate_by_mllm(plan, video_path, type='video')
                iter += 1
        if "time_cost" in plan:
            time = plan["time_cost"]
        else:
            time = '8'
        merge_video_audio(video_path, self.curr_audio_path, time, self.final_video_path)
        return self.final_video_path
    
    def captioning_single_work(self, plan, eval_results=None):
        if eval_results==None:
            prompt_r = " Please use {} and {} as the materials to depict a image scene that a diffusion model can understand and generate. Return the prompt ONLY".format(plan["scenario"], plan["prompt"])
            plan["prompt"] = eval(
            self.art_agent(
                    prompt=prompt_r+ "\n" + plan["prompt"],
            ))
        else:
            plan["prompt"] = eval(
            self.art_agent(
                    prompt=eval_results + "\n" + "\n" +"Please provide new prompt to depict a image scene. Be relative to" +  plan["prompt"]+ "Return the prompt ONLY.",
            ))
        image_url= self.captioning_tool.query(plan["prompt"])
        return image_url
    
    def captioning_work(self, scene_idx):
        video_success = False
        iter=0
        plan = self.final_plan[scene_idx]
        eval_results = None
        
        self.curr_image_path = self.curr_scene_dir/"image.png"
        self.curr_audio_path = self._ensure_audio(plan["audio_content"])
        if os.path.exists(self.curr_image_path):
            pass
        else:
            while video_success == False and iter < self.max_generate_iteration:
                image_path = self.curr_scene_dir/"test{}.png".format(iter)
                if not os.path.exists(image_path):
                    image_url = self.captioning_single_work(plan, eval_results)
                    image_path = download_file(image_url, image_path)
                video_success, eval_results = self.video_evaluate_by_mllm(plan, [image_path], type='image')
                iter += 1
            with Image.open(image_path) as img:
                img.save(self.curr_image_path)
        
        self.final_video_path = self.curr_scene_dir/"scene{}.mp4".format(scene_idx)
        if "time_cost" in plan:
            time = plan["time_cost"]
        else:
            time = '8'
        image_to_video(image_path, self.curr_audio_path, time, self.final_video_path)
        return self.final_video_path

    def talking_head_single_work(self, audio_url, final_video_path):
        video_url = self.talking_head_tool.generate_and_download(audio_url, final_video_path)
        return video_url
    
    def talking_head_work(self, scene_idx):
        plan = self.final_plan[scene_idx]
        self.final_video_path = self.curr_scene_dir/"scene{}.mp4".format(scene_idx)
        audio_url = self._ensure_audio(plan["audio_content"], return_url=True)
        if os.path.exists(self.final_video_path):
            pass
        else:
            video_url = self.talking_head_single_work(audio_url, self.final_video_path)
            self.final_video_path = download_file(video_url, self.curr_scene_dir/"scene{}.mp4".format(scene_idx))
        return self.final_video_path
    
    def slides_single_work(self, scene_idx, plan, image_path, eval_results=None):
        if eval_results==None and (os.path.exists(image_path) is False):
            prompt_r = (
                f"Please return the type and index of the {plan['source']} in the PDF "
                "with the dict: {'type': TABLE/IMAGE, 'number': INT}"
                "where a is TABLE or IMAGE, and b is its index."
            )
            crop_dict = eval(
            self.planner(
                prompt=prompt_r,
                pdf_path=Path(self.pdf_path),
            ))
            result = _load_json_dict(crop_dict)
            image_path = get_specific_element(self.pdf_path, result['type'], result['number'], image_path)
            
        else:
            if not eval_results:
                eval_results = ''
            self.final_plan[scene_idx]["prompt"] = eval(
            self.planner(
                prompt= 'With this reason'+ eval_results+"Provide a better prompt"+eval_results+"\n Old prompt is"+plan['prompt'] +"\n RETURN new prompt ***ONLY***",
                pdf_path=Path(self.pdf_path),
            ))

        return image_path
        
    def slides_work(self, scene_idx):
        video_success = False
        iter=0
        image_path =  self.curr_scene_dir/"image{}.png".format(iter)
        plan = self.final_plan[scene_idx]
        eval_results = None
        self.final_video_path = self.curr_scene_dir/"scene{}.mp4".format(scene_idx)
        self.curr_image_path = self.curr_scene_dir/"image.png"
        self.curr_audio_path = self._ensure_audio(plan["audio_content"])
        if os.path.exists(self.curr_image_path):
            image_path = self.curr_image_path
            pass
        else:
            while video_success == False and iter < self.max_generate_iteration:
                image_path = self.curr_scene_dir/"image{}.png".format(0)
                self.slides_single_work(scene_idx, plan, image_path, eval_results)
                video_success, eval_results = self.video_evaluate_by_mllm(plan, [image_path], type='image') 
                iter += 1
            #with Image.open(self.curr_image_path) as img:
                #img.save(self.curr_image_path)
            self.curr_image_path = create_ppt_style_image(image_path, plan['prompt'], self.curr_image_path)
        
        if "time_cost" in plan:
            time = plan["time_cost"]
        else:
            time = '8'
        image_to_video(self.curr_image_path, self.curr_audio_path, time, self.final_video_path)
        return self.final_video_path
        
    def video_evaluate_by_mllm(self, plan, video_path, type='video'):
        if type=='video':
            img_list = extract_key_frames(video_path)
        elif type=='image':
            img_list = image_to_images(video_path)
        else:
            img_list = None
        if "general" in plan["style"].lower():
            prompt_e = plan["prompt"] + ' \n '+ prompts.gen_vis_eval
        elif "professional" in plan["style"].lower():
            prompt_e =  plan["scenario"] + ' \n '+   plan["prompt"] + ' \n '+ prompts.pro_vis_eval 
        elif "captioning" in plan["style"].lower():
            prompt_e = prompts.gen_vis_eval
        elif "slides" in plan["style"].lower():
            prompt_e = prompts.slides_vis_eval+plan['prompt']
        else: print("error: Please check the style file of"+plan["scenario"])
        eval_results = eval(
            self.evaluator(
                prompt = prompt_e,
                img_path=img_list,
                ))
        success = classify_response(eval_results)
        return success, eval_results
    
    def setting_plan_format(self, plan, step="low"):
        if step == "high":
            prompt = prompts.high_plan_format_prompt + ' \n '+ plan  
        else:
            prompt = plan + ' \n '+ prompts.low_plan_format_prompt
        plan_legal = eval(
            self.planner(
                prompt=prompt,
                pdf_path=Path(self.pdf_path),
            )
        )
        #self.workflow_logger.info(f"low_plan_legal: {low_plan_legal}")
        if _load_json_dict(plan_legal) and step=='low':
            self.final_plan[self.scene_idx] = _load_json_dict(plan_legal)
        return  plan_legal

    def _prepare_dir(self, input_path, output_dir) -> None:

        pdf_name = input_path.stem
        self.input_path = input_path
        self.work_dir = output_dir / pdf_name
        if not os.path.isdir(self.work_dir):
            self.work_dir.mkdir(parents=True)

        self.log_dir = self.work_dir / "logs"
        if not os.path.isdir(self.log_dir):
            self.log_dir.mkdir()
        self.qa_path = self.log_dir / "llm_qa.md"
        self.workflow_path = self.log_dir / "workflow.log"
        self.high_plan_path = self.log_dir / "highplan.txt"
        self.final_video_path_= self.log_dir / "final_video.mp4"
        self.animate_path =  Path("utils/math_vis.py").resolve()
        #self.plan_path = self.log_dir


    # def tolist(self, high_plan: str) -> list:
    #     if self.plan_by=='GEMINI':
    #         return text_to_list(high_plan)

