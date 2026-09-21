"""使用本地 Transformers 权重的 Qwen 推理客户端。"""

import os

import torch
from transformers import AutoProcessor, Qwen3VLForConditionalGeneration

DEFAULT_MODEL_PATH = r"G:\LLM\modelscope\hub\models\qwen\Qwen3-VL-2B-Instruct"
_local_client = None


class LocalQwenClient:
    """把本地 Qwen 模型封装成 generate(prompt) 客户端。"""

    def __init__(
        self,
        model_path: str | None = None,
        max_new_tokens: int = 1024,
    ) -> None:
        self.model_path = model_path or os.getenv(
            "LOCAL_QWEN_MODEL_PATH",
            DEFAULT_MODEL_PATH,
        )
        self.max_new_tokens = max_new_tokens
        self.processor = None
        self.model = None

    def load(self) -> None:
        """首次调用时加载模型，避免只导入模块就占用显存。"""

        if self.model is not None:
            return

        self.processor = AutoProcessor.from_pretrained(
            self.model_path,
            local_files_only=True,
        )
        self.model = Qwen3VLForConditionalGeneration.from_pretrained(
            self.model_path,
            device_map="auto",
            local_files_only=True,
        )

    def generate(self, prompt: str) -> str:
        """执行一次本地文本生成。"""

        self.load()

        messages = [
            {
                "role": "user",
                "content": [{"type": "text", "text": prompt}],
            }
        ]
        text = self.processor.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        inputs = self.processor(text=[text], return_tensors="pt")
        inputs = {key: value.to(self.model.device) for key, value in inputs.items()}

        with torch.inference_mode():
            generated = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
            )

        # 输入部分不是模型生成内容，需要从输出中裁掉。
        generated = generated[:, inputs["input_ids"].shape[1]:]
        output = self.processor.batch_decode(
            generated,
            skip_special_tokens=True,
        )[0]

        return output.strip()


def get_local_qwen_client() -> LocalQwenClient:
    """返回进程内复用的本地 Qwen 客户端。"""

    global _local_client

    if _local_client is None:
        _local_client = LocalQwenClient()

    return _local_client