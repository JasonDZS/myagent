#!/usr/bin/env python3
"""Setup script for MyAgent WebSocket server CLI."""

import os
import sys
from pathlib import Path


def setup_cli():
    """设置 CLI 工具"""
    print("🔧 正在设置 MyAgent WebSocket CLI...")

    # 获取项目根目录
    project_root = Path(__file__).parent
    cli_script = project_root / "scripts" / "myagent-ws"

    # 检查脚本是否存在
    if not cli_script.exists():
        print(f"❌ CLI 脚本不存在: {cli_script}")
        return False

    # 使脚本可执行
    os.chmod(cli_script, 0o755)

    # 尝试创建符号链接到系统路径
    system_paths = [
        "/usr/local/bin",
        os.path.expanduser("~/.local/bin"),
        os.path.expanduser("~/bin"),
    ]

    installed = False
    for bin_path in system_paths:
        try:
            bin_dir = Path(bin_path)
            if bin_dir.exists() and os.access(bin_dir, os.W_OK):
                target = bin_dir / "myagent-ws"

                # 移除已存在的链接
                if target.exists() or target.is_symlink():
                    target.unlink()

                # 创建符号链接
                target.symlink_to(cli_script)
                print(f"✅ CLI 工具已安装到: {target}")
                installed = True
                break
        except (OSError, PermissionError):
            continue

    if not installed:
        print("⚠️  无法安装到系统路径，您可以：")
        print(f"   1. 直接运行: {cli_script}")
        print(f"   2. 添加到 PATH: export PATH=$PATH:{cli_script.parent}")
        print(f"   3. 手动创建链接: ln -s {cli_script} ~/.local/bin/myagent-ws")

    return True


def check_dependencies():
    """检查依赖"""
    print("🔍 正在检查依赖...")

    required_packages = ["websockets", "pydantic", "openai"]

    missing = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print(f"❌ 缺少依赖包: {', '.join(missing)}")
        print("请运行: pip install -r requirements-ws.txt")
        return False

    print("✅ 依赖检查通过")
    return True


def create_example():
    """创建示例 Agent 文件"""
    print("📝 创建示例文件...")

    example_content = '''"""简单的 Hello World Agent 示例"""

from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult

class HelloTool(BaseTool):
    name: str = "say_hello"
    description: str = "向用户问好"
    parameters: dict = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "用户名称"}
        },
        "required": ["name"]
    }

    async def execute(self, name: str) -> ToolResult:
        return ToolResult(output=f"你好, {name}! 欢迎使用 MyAgent WebSocket 服务！")

# 必须命名为 'agent'
agent = create_react_agent(
    name="hello-assistant",
    tools=[HelloTool()],
    system_prompt="你是一个友好的助手，会使用 say_hello 工具向用户问好。",
    max_steps=3
)
'''

    example_file = Path("hello_agent.py")
    if not example_file.exists():
        example_file.write_text(example_content)
        print(f"✅ 示例文件已创建: {example_file}")
    else:
        print(f"ℹ️  示例文件已存在: {example_file}")

    return example_file


def main():
    """主函数"""
    print("🚀 MyAgent WebSocket Server 安装程序\\n")

    # 检查 Python 版本
    if sys.version_info < (3, 8):
        print("❌ 需要 Python 3.8 或更高版本")
        sys.exit(1)

    try:
        # 检查依赖
        deps_ok = check_dependencies()

        # 设置 CLI
        cli_ok = setup_cli()

        # 创建示例
        example_file = create_example()

        print("\\n" + "=" * 50)
        if deps_ok and cli_ok:
            print("🎉 安装完成！")
            print("\\n快速开始：")
            print(f"  myagent-ws server {example_file}")
            print("  然后访问 ws://localhost:8080")
        else:
            print("⚠️  安装部分完成，请检查上述错误信息")

        print("\\n更多帮助：")
        print("  myagent-ws --help")
        print("  查看文档: docs/ws-server/quick-start.md")

    except KeyboardInterrupt:
        print("\\n❌ 安装被中断")
        sys.exit(130)
    except Exception as e:
        print(f"❌ 安装出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
