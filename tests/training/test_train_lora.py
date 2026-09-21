"""LoRA 训练配置测试。"""

import json

import pytest
from pydantic import ValidationError

from training.train_lora import load_config


def test_load_lora_config(tmp_path) -> None:
    """配置应能从 JSON 正确加载。"""

    config_path = tmp_path / "lora.json"
    config_path.write_text(
        json.dumps(
            {
                "base_model_path": "base-model",
                "train_data_path": "train.jsonl",
                "valid_data_path": "valid.jsonl",
                "output_dir": "adapter",
            }
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.base_model_path == "base-model"
    assert config.valid_data_path == "valid.jsonl"


def test_lora_config_requires_base_model(tmp_path) -> None:
    """缺少 base model 的配置应被拒绝。"""

    config_path = tmp_path / "lora.json"
    config_path.write_text(
        json.dumps({"train_data_path": "train.jsonl", "output_dir": "adapter"}),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_config(config_path)