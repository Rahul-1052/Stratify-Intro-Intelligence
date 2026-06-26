import json
import torch
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
from qwen_vl_utils import process_vision_info


MODEL_ID = "Qwen/Qwen2.5-VL-3B-Instruct"

_processor = None
_model = None


def _get_model():
    global _processor, _model

    if _processor is None:
        _processor = AutoProcessor.from_pretrained(MODEL_ID)

    if _model is None:
        _model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
            MODEL_ID,
            torch_dtype=torch.float16,
            device_map="auto",
        )

    return _processor, _model


def _clean_json_output(text):
    cleaned = text.strip()

    if cleaned.startswith("```json"):
        cleaned = cleaned.replace("```json", "", 1).strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```", "", 1).strip()

    if cleaned.endswith("```"):
        cleaned = cleaned[:-3].strip()

    return cleaned


def observe_intro(frame_paths, vision=None, video=None):
    """
    VLM observation layer.

    Responsibility:
    Observe what happens in the intro.
    Do not recommend.
    Do not compare.
    Do not claim causation.
    """

    if not frame_paths:
        return {
            "status": "failed",
            "observations": {},
            "confidence": "low",
            "warnings": ["No intro frames available for VLM observation."],
        }

    selected_frames = frame_paths[:4]

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

    try:
        processor, model = _get_model()

        messages = [
            {
                "role": "user",
                "content": [{"type": "image", "image": path} for path in selected_frames]
                + [{"type": "text", "text": prompt}],
            }
        ]

        text = processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

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

        cleaned = _clean_json_output(output_text)
        parsed = json.loads(cleaned)

        return {
            "status": "success",
            "observations": parsed,
            "confidence": parsed.get("confidence", "low"),
            "warnings": [],
        }

    except Exception as e:
        return {
            "status": "failed",
            "observations": {},
            "confidence": "low",
            "warnings": [f"VLM observation failed: {str(e)}"],
        }