import json
import torch
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from qwen_vl_utils import process_vision_info

MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"

FRAME_PATHS = [
    "temp_frames/OO7YWIzHG9w_intro/frame_001.jpg",
    "temp_frames/OO7YWIzHG9w_intro/frame_005.jpg",
    "temp_frames/OO7YWIzHG9w_intro/frame_010.jpg",
    "temp_frames/OO7YWIzHG9w_intro/frame_015.jpg",
]

processor = AutoProcessor.from_pretrained(MODEL_ID)
model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float16,
    device_map="auto",
)

prompt = """
You are Stratify's intro observation engine.

Observe these frames as a sequence from a video intro.

Return JSON only.
Do not give advice.
Do not explain performance.
Do not claim causation.

Schema:
{
  "opening_type": "",
  "attention_focus": "",
  "first_meaningful_action": "",
  "movement_progression": "",
  "emotional_impression": "",
  "visual_focus": "",
  "confidence": "low|moderate|high"
}
"""

messages = [
    {
        "role": "user",
        "content": [{"type": "image", "image": path} for path in FRAME_PATHS]
        + [{"type": "text", "text": prompt}],
    }
]

text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
image_inputs, video_inputs = process_vision_info(messages)

inputs = processor(
    text=[text],
    images=image_inputs,
    videos=video_inputs,
    padding=True,
    return_tensors="pt",
).to("cuda")

with torch.no_grad():
    output_ids = model.generate(**inputs, max_new_tokens=220)

generated_ids = [
    output_ids[len(input_ids):]
    for input_ids, output_ids in zip(inputs.input_ids, output_ids)
]

output_text = processor.batch_decode(
    generated_ids,
    skip_special_tokens=True,
    clean_up_tokenization_spaces=False,
)[0]

print(output_text)

try:
    cleaned = output_text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    parsed = json.loads(cleaned)

    print("\nParsed JSON:")
    print(json.dumps(parsed, indent=2))

except Exception as e:
    print("\nJSON parse failed:", e)