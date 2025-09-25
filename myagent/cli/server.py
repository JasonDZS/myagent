"""CLI for MyAgent WebSocket server deployment."""

import argparse
import asyncio
import importlib.util
import sys
import signal
from pathlib import Path
from typing import Callable, Any

from ..ws.server import AgentWebSocketServer
from ..logger import logger


def load_agent_from_file(file_path: str) -> Callable[[], Any]:
    """从 Python 文件动态加载 Agent"""
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        raise FileNotFoundError(f"❌ Agent 文件不存在: {file_path}")
    
    if not file_path.suffix == '.py':
        raise ValueError(f"❌ Agent 文件必须是 Python 文件: {file_path}")
    
    try:
        # 动态加载模块
        spec = importlib.util.spec_from_file_location("agent_module", file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")
            
        module = importlib.util.module_from_spec(spec)
        
        # 将模块添加到 sys.modules 以避免导入问题
        sys.modules["agent_module"] = module
        spec.loader.exec_module(module)
        
        # 查找 agent 变量
        if not hasattr(module, 'agent'):
            raise AttributeError(
                f"❌ 在 {file_path} 中未找到 'agent' 变量\\n"
                f"请确保文件中定义了名为 'agent' 的变量"
            )
        
        agent_template = module.agent
        
        # 验证是否为有效的 Agent 实例
        if not hasattr(agent_template, 'run') and not hasattr(agent_template, 'arun'):
            raise AttributeError(
                f"❌ agent 变量不是有效的 Agent 实例\\n"
                f"Agent 必须有 'run' 或 'arun' 方法"
            )
        
        # 创建工厂函数，每次调用都重新执行模块来创建新实例
        def agent_factory():
            try:
                # 重新执行模块以创建全新的实例，避免深拷贝问题
                fresh_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(fresh_module)
                
                if not hasattr(fresh_module, 'agent'):
                    raise AttributeError("Agent module must contain 'agent' variable")
                
                return fresh_module.agent
            except Exception as e:
                logger.error(f"Failed to create agent instance: {e}")
                raise RuntimeError(f"Could not create agent instance: {e}")
        
        return agent_factory
        
    except ImportError as e:
        raise ImportError(f"❌ 导入 Agent 文件失败: {e}")
    except SyntaxError as e:
        raise SyntaxError(f"❌ Agent 文件语法错误: {e}")
    except Exception as e:
        raise RuntimeError(f"❌ 加载 Agent 文件时出错: {e}")


async def run_server(args):
    """运行 WebSocket 服务器"""
    print(f"🔍 正在加载 Agent 文件: {args.agent_file}")
    
    try:
        agent_factory = load_agent_from_file(args.agent_file)
        
        # 测试 agent 创建
        test_agent = agent_factory()
        agent_name = getattr(test_agent, 'name', 'unknown')
        print(f"✅ Agent 加载成功: {agent_name}")
        
    except Exception as e:
        print(f"❌ {e}")
        return 1
    
    # 创建服务器
    server = AgentWebSocketServer(
        agent_factory_func=agent_factory,
        host=args.host,
        port=args.port
    )
    
    # 设置 asyncio 信号处理器优雅关闭
    loop = asyncio.get_running_loop()
    shutdown_requested = False
    
    def handle_shutdown():
        nonlocal shutdown_requested
        if not shutdown_requested:
            shutdown_requested = True
            print("\\n🛑 正在关闭服务器...")
            # 创建关闭任务
            loop.create_task(server.shutdown())
    
    # 使用 asyncio 的信号处理，这在事件循环中工作更好
    loop.add_signal_handler(signal.SIGINT, handle_shutdown)
    loop.add_signal_handler(signal.SIGTERM, handle_shutdown)
    
    try:
        await server.start_server()
        print("🛑 服务器已停止")
        return 0
    except KeyboardInterrupt:
        print("\\n🛑 服务器已停止")  
        return 0
    except Exception as e:
        print(f"❌ 服务器错误: {e}")
        return 1


def create_server_parser(subparsers):
    """创建 server 子命令解析器"""
    server_parser = subparsers.add_parser(
        "server",
        help="启动 MyAgent WebSocket 服务器",
        description="将 MyAgent 实例部署为 WebSocket 服务"
    )
    
    server_parser.add_argument(
        "agent_file",
        help="Agent 配置文件路径 (Python 文件，必须包含 'agent' 变量)"
    )
    
    server_parser.add_argument(
        "--host",
        default="localhost",
        help="服务器主机地址 (默认: localhost)"
    )
    
    server_parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="服务器端口 (默认: 8080)"
    )
    
    server_parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    return server_parser


def main():
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="myagent-ws",
        description="MyAgent WebSocket 部署工具",
        epilog="""
示例:
  myagent-ws server my_agent.py                    # 启动服务器
  myagent-ws server my_agent.py --host 0.0.0.0     # 监听所有地址
  myagent-ws server my_agent.py --port 9000        # 指定端口
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="MyAgent WebSocket Server 1.0.0"
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        help="可用命令",
        metavar="COMMAND"
    )
    
    # server 子命令
    create_server_parser(subparsers)
    
    # 解析参数
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # 设置日志级别
    if getattr(args, 'debug', False):
        import logging
        logging.basicConfig(level=logging.DEBUG)
        logger.setLevel(logging.DEBUG)
    
    # 执行命令
    if args.command == "server":
        try:
            return asyncio.run(run_server(args))
        except KeyboardInterrupt:
            print("\\n🛑 操作被中断")
            return 130
    
    return 0


if __name__ == "__main__":
    sys.exit(main())