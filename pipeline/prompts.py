system_message = "You are an expert in reading academic papers and creating video summaries based on them. "

math_prompt = "You are an expert in reading academic papers and creating video summaries based on them. "

high_level_planning_prompt = "Given a paper, please design around 10 concise scene descriptions that summarize its key contributions with strong logic relation. Requirements: Each scene nclude strong relationship between last and next scene. No overlapping content between scenes. Collectively present all key findings in a coherent narrative. Maintain high technical accuracy and professionalism. Allow 5 to 10 seconds of video per scene. Deliver only core content; omit acknowledgements and references."

high_level_evaluate_prompt = "Below are the video-summary scenes I designed based on the corresponding paper. Please check it with answering questions: Do these scenes cover all the key points the original paper intends to convey? Do these scenes avoid overlapping content and redundancy? Do these scenes form a coherent and correct story? Please answer “YES/NO.” If you answer “NO” (i.e., issues exist), provide suggestions for improvement. Current plan:"

high_level_replanning_prompt = "The above are the scenes you previously designed. Please modify the scenes accordingly based on the following feedback while keeping the format unchanged:"

high_plan_format_prompt = " The next paragraph of TEXT will provide descriptions for multiple scenes. I need you to fill the \"***\" section of the dict LIST with the TEXT. Please output the LIST only. LIST:[{ \"SCENE1\": \"******\", \"DESCRIPTION\": \"******\", \"TIME_ALLOCATION\": \"******\"},{ \"SCENE2\": \"******\", \"DESCRIPTION\": \"******\", \"TIME_ALLOCATION\": \"******\"}...] TEXT:"

low_level_planning_prompt = {
  "task": "Your task is to select an appropriate presentation style for the scenario (strictly choosing one style from Slides, Professional, Talking Heads, Captioning, or General Video styles) of the scene I give you at last.",
  "considerations": "Please consider the dynamics, themes, and content of the original text comprehensively.",
  "assistance": "To assist you, I have designed the following questions.",
  "instructions": [
    {
      "Question 1": "Can this scenario be described using one or two important image/table from the original paper?",
      "yes": {
        "action": "Confirm the video style as Slides style.",
        "next_step": "Proceed to Act1."
      },
      "no": {
        "next_step": "Go to Question 2."
      }
    },
    {
      "Question 2": "If the scenario includes professional contents like MOL structure presentation or involves the presentation of mathematical principles?",
      "yes": {
        "action": "Confirm the video style as Professional style.",
        "next_step": "Proceed to Act2."
      },
      "no": {
        "next_step": "Go to Question 3."
      }
    },
    {
      "Question 3": "Is the content of this scene suitable to be presented as a speech by an appropriate character in front of the camera?",
      "yes": {
        "action": "Confirm the video style as Talking Heads style.",
        "next_step": "Proceed to Act3."
      },
      "no": {
        "next_step": "Go to Question 4."
      }
    },
    {
      "Question 4": "Is the scene directly represented by existing real photos?",
      "yes": {
        "next_step": "Proceed to Act4."
      },
      "no": {
        "next_step": "Proceed to Act5."
      }
    }
  ],
  "actions": {
    "Act1": {
      "requirement": "Provide the SPECIFIC position of the important picture/table in the paper so I can find it easily.",
      "content": [
        "Provide 'Prompt' and 'Audio Content' to describe it.",
        "Ensure it does not exceed the allocated time.",
        "Complete the answering table."
      ]
    },
    "Act2": {
      "requirement": "Is the professional content of this video related to molecular visualization or mathematical formulas?",
      "content": [
        "Provide related content.",
        "Provide 'Prompt' and 'Audio Content' to describe it.",
        "Ensure it does not exceed the allocated time."
      ]
    },
    "Act3": {
      "requirement": "Describe this person's appearance and identity so I can retrieve the proper person.",
      "content": [
        "What does he/she say?",
        "Provide the 'Audio Content'.",
        "Ensure it does not exceed the allocated time."
      ]
    },
    "Act4": {
      "requirement": "Does the depicted scene include any dynamic elements, making it better suited for video description rather than static photos?",
      "yes": {
        "action": "Confirm the video style as General Video style.",
        "requirement": "Provide a textual description that can be used to retrieve photos and Prompt for AI-generated videos."
      },
      "no": {
        "action": "Confirm the video style as Captioning style.",
        "requirement": "Only provide a textual description for retrieving photos."
      },
      "additional": "In any case, you must provide narration describing the scene, ensuring it does not exceed the allocated time."
    },
    "Act5": {
      "requirement": "Does the depicted scene include any dynamic elements, making it better suited for video description rather than static images?",
      "yes": {
        "action": "Confirm the video style as General Video style.",
        "requirement": "Provide a textual description that can be used to retrieve photos and prompts for AI-generated videos."
      },
      "no": {
        "action": "Confirm the video style as Captioning style.",
        "requirement": "Only provide a textual description for retrieving photos."
      },
      "additional": "In any case, you must provide narration describing the scene, ensuring it does not exceed the allocated time."
    }
  },
  "notice": [
    "If you choose SLIDES style, you must provide the corresponding material position (Like Fig1, or Table2), not textual content!",
    "Besides, design audio content that can be spoken for humans to describe the scene, \" TIME_ALLOCATION \" is already given, donot change!."
  ],
  "Scene":"Here is the Scene provided to you:"
}


low_level_evaluate_prompt = "This is the video summary plan we created for the scene of the part of the paper. Please respond to each of the following questions with either \"YES\" or \"NO\" to determine whether the current plan meets the requirements (if \"NO\", provide the correct answer)."

low_level_replanning_prompt = "The above is the scene style selection plan you designed earlier, but it seems that the following issues have arisen. Please make the corresponding modifications and ensure that the updated version maintains the exact same format as the previous version.:"

low_plan_format_prompt="Fill in the dictionary (***** means blank ) with the given above text. For \"style,\" the blank can only be filled with one of the following options: (Slides, Professional, Talking Heads, Captioning, or General Video). If there is no suitable match, write \"PASS\":{ \"audio_content\": \"******\", \"style\": \"******\", \"source\": \"******\", \" prompt\": \"******\"} Only output this dictionary, no extra content is needed! For example: { \"audio_content\": \"This is the picture from the original paper, which means a lot.\",\"style\": \"Slides\",\"source\": \"Fig.1\",\"prompt\": \"Previous palaeomagnetic investigations using samples from Apollo and Chang'e-5 missions have revealed the Moon's magnetic history. However, these studies were limited to the nearside, leaving the farside largely unexplored.\". \n Make sure that the content replacing \"******\" are strings and does not contain double quotes inside.}"

low_level_evaluate_prompt_list = ["\n Is the video style exactly one of those choices: [Slides, Professional, Talking Heads, Captioning, or General Video] ? \n Do you think the choice of this style is reasonable?", "\n Does the \" audio_ content\" part appear to meet the required time_cost? Avoid overly lengthy text. The time_cost is fixed and cannot be changed. \n Do you think the audio_content is reasonable?","  Only If the video \" style \" is \" slides \", answer: Does the \" source \" part explicitly provide a specific source element (exact table/picture/equation)in the original paper? \n Is the professionalism of the current plan acceptable? \n Only if the video \"style \"  is \" professional \", does the original plan provide a clear mathematical expression or molecular formula so that I can know the content without reading original paper? \n","The \"prompt\" part should be a description of the scenes for the video to be generated. Does the existing \"prompt\" work as a prompt for a generation model (if the style is a General video, Captioning) or as a note to show (if the style is Slides or Professional)?\n"] 

load_table_prompt="Can you return the content of the specific table of the original paper in table fomular? No extra TEXT in output."

pro_classify_prompt = "Is this scene related to mathematical content? If yes, output \"math\". Is this scene related to molecular visualization content? If yes, output \"mol\""

pro_format_prompt = "The code I require does not need to be complete; it only needs to exist as an animation function. Please check if the following code meets my requirements: It should not contain any import statements. It should be simple and within 100 lines! It should start with 'def animate(self):\n    '. It should end with 'self.wait(X)' (where X is a number). Conforms to indentation rules! If it does not meet the requirements, rewrite it in the format I requested. Output the code Only!"

pro_gen_prompt = "Why can't the following code run? Please modify the code and make it generate the correct video. Your result must be understandable by the Python compiler! Conforms to indentation rules. Make it SIMPLE and meaningful! Make sure the code Only output the code!"

pro_vis_eval = "This is the video we created to introduce the above content, and I would like you to answer the following questions with (\"YES\" or \"NO\") to determine if the current video meets the requirements while maintaining structural integrity. If the answer is \"NO,\" please provide a reason:Is there visual content (animation) in the bottom left corner of the video? Is the animation in the video reasonable and mathematically strong? Do the visual content and text avoid meanlingless overlap in the video?"

pro_vis_rege = "The code you write has the following issues, please output the updated code ONLY:"

gen_vis_eval = "This is the video we created to introduce the above content, and I would like you to answer the following questions with (\"YES\" or \"NO\") to determine if the current video meets the requirements while maintaining structural integrity. If the answer is \"NO,\" please provide a reason:  Does it convey serious subject matter? Is the image filled with vivid scenes rather than meaningless numbers, letters, and symbols? Is the image strongly relevant to the following description?"

slides_vis_eval = "This is the video we created to introduce the above content, and I would like you to answer the following questions with (\"YES\" or \"NO\") . Is the following text works well as a caption beneath an image in a PowerPoint slide?  Is the following text explaining the image? Following text:"