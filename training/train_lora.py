"""使用 Transformers Trainer 和 PEFT 执行 LoRA-SFT。"""

import argparse
import json
from pathlib import Path

import torch
from peft import LoraConfig, TaskType, get_peft_model
from pydantic import BaseModel
from torch.utils.data import Dataset
from transformers import (
    AutoTokenizer,
    DataCollatorForLanguageModeling,
    Qwen3VLForConditionalGeneration,
    Trainer,
    TrainingArguments,
)


class LoRATrainingConfig(BaseModel):
    """一次 LoRA-SFT 运行需要的全部配置。"""

    base_model_path: str
    train_data_path: str
    valid_data_path: str | None = None
    output_dir: str
    max_length: int = 1024
    batch_size: int = 1
    gradient_accumulation_steps: int = 8
    learning_rate: float = 2e-4
    num_train_epochs: float = 1
    max_steps: int = -1
    logging_steps: int = 1
    eval_steps: int = 10
    save_steps: int = 10
    lora_r: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    target_modules: list[str] = ["q_proj", "v_proj"]
    bf16: bool = True


def load_config(config_path: str | Path) -> LoRATrainingConfig:
    """从 JSON 文件读取训练配置。"""

    data = json.loads(Path(config_path).read_text(encoding="utf-8"))
    return LoRATrainingConfig.model_validate(data)


def _load_rows(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class SFTDataset(Dataset):
    """把 Chat messages 转成因果语言模型训练样本。"""

    def __init__(self, rows: list[dict], tokenizer, max_length: int) -> None:
        self.rows = rows
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict:
        row = self.rows[index]
        text = self.tokenizer.apply_chat_template(
            row["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
        encoded = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            return_tensors=None,
        )
        encoded["labels"] = list(encoded["input_ids"])
        return encoded


def train_lora(config: LoRATrainingConfig) -> str:
    """执行 LoRA-SFT，并把 adapter 保存到 output_dir。"""

    tokenizer = AutoTokenizer.from_pretrained(
        config.base_model_path,
        local_files_only=True,
    )

    model = Qwen3VLForConditionalGeneration.from_pretrained(
        config.base_model_path,
        dtype=torch.bfloat16 if config.bf16 else torch.float32,
        device_map="auto",
        local_files_only=True,
    )
    model.config.use_cache = False

    model = get_peft_model(
        model,
        LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=config.lora_r,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            target_modules=config.target_modules,
        ),
    )

    train_dataset = SFTDataset(
        _load_rows(config.train_data_path),
        tokenizer,
        config.max_length,
    )
    eval_dataset = (
        SFTDataset(_load_rows(config.valid_data_path), tokenizer, config.max_length)
        if config.valid_data_path
        else None
    )

    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=config.batch_size,
        per_device_eval_batch_size=config.batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        learning_rate=config.learning_rate,
        num_train_epochs=config.num_train_epochs,
        max_steps=config.max_steps,
        logging_steps=config.logging_steps,
        eval_strategy="steps" if eval_dataset is not None else "no",
        eval_steps=config.eval_steps,
        save_strategy="steps",
        save_steps=config.save_steps,
        bf16=config.bf16,
        report_to=[],
        remove_unused_columns=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False),
    )

    trainer.train()
    trainer.save_model(str(output_dir))
    trainer.save_state()
    return str(output_dir)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, help="LoRA training JSON config")
    args = parser.parse_args()
    output_dir = train_lora(load_config(args.config))
    print(f"adapter_saved={output_dir}")


if __name__ == "__main__":
    main()