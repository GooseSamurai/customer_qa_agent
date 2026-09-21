"""T001 工程骨架的冒烟测试。

“冒烟测试”不是测试业务功能，而是先确认项目最基本的能力没有坏：
所有约定好的业务目录都能被 Python 正常导入。

执行入口：
    在项目根目录运行 `python -m pytest`
"""

# import_module 可以像 `import schemas` 一样，根据字符串名称导入模块。
from importlib import import_module
from pathlib import Path

# pytest 会识别 test_*.py 文件和 test_* 函数，并执行其中的断言。
import pytest

# __file__ 是当前测试文件路径。
# resolve() 把它转换为绝对路径。
# parents[0] 是 tests/，parents[1] 是项目根目录。
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 这 12 个名字是项目约定存在、并且必须可以 import 的业务 package。
BUSINESS_PACKAGES = (
    "schemas",
    "model",
    "agent",
    "tools",
    "rag",
    "evidence",
    "training",
    "feedback",
    "serving",
    "api",
    "db",
    "evaluation",
)


# parametrize 会把 BUSINESS_PACKAGES 中的每一项依次传给 package_name。
# 因此下面这个测试函数实际会运行 12 次，而不是只运行 1 次。
@pytest.mark.parametrize("package_name", BUSINESS_PACKAGES)
def test_business_packages_are_importable(package_name: str) -> None:
    """正常路径：每个业务 package 都应该可以被 Python 导入。"""

    # 如果 package 不存在或内部代码报错，这一行会直接让测试失败。
    module = import_module(package_name)

    # import_module 成功时会返回 module 对象，而不是 None。
    assert module is not None


def test_business_packages_resolve_from_project_root() -> None:
    """边界检查：导入的必须是本项目代码，而不是其他环境中的同名包。"""

    for package_name in BUSINESS_PACKAGES:
        # 根据名称导入 package。
        module = import_module(package_name)

        # __file__ 是 Python 实际加载的文件路径。
        module_path = Path(module.__file__).resolve()

        # 如果 `model` 等通用名称被导入成 site-packages 中的其他包，
        # 这条断言会失败，并在报告里显示真实加载路径。
        assert module_path.is_relative_to(PROJECT_ROOT), (
            f"{package_name} resolved outside the project: {module_path}"
        )