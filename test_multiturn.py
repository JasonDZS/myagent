#!/usr/bin/env python3
"""测试多轮对话功能的WebSocket客户端"""

import asyncio
import json
import websockets
import uuid


class WebSocketTester:
    def __init__(self, url="ws://localhost:8889"):
        self.url = url
        self.websocket = None
        self.session_id = None
        
    async def connect(self):
        """连接到WebSocket服务器"""
        print(f"🔌 连接到 {self.url}")
        self.websocket = await websockets.connect(self.url)
        print("✅ 连接成功")
        
        # 等待连接确认
        response = await self.websocket.recv()
        data = json.loads(response)
        print(f"📨 服务器响应: {data}")
        
    async def create_session(self):
        """创建会话"""
        print("🆕 创建新会话")
        create_msg = {
            "event": "user.create_session",
            "content": "创建天气助手会话"
        }
        
        await self.websocket.send(json.dumps(create_msg))
        response = await self.websocket.recv()
        data = json.loads(response)
        
        if data.get("event") == "agent.session_created":
            self.session_id = data.get("session_id")
            print(f"✅ 会话创建成功: {self.session_id}")
        else:
            print(f"❌ 会话创建失败: {data}")
            
    async def send_message(self, content):
        """发送消息给agent"""
        print(f"\n👤 用户消息: {content}")
        
        message = {
            "event": "user.message",
            "session_id": self.session_id,
            "content": content
        }
        
        await self.websocket.send(json.dumps(message))
        
        # 监听agent响应
        print("🤖 Agent响应:")
        timeout_counter = 0
        max_timeout = 20  # 20秒超时
        
        while timeout_counter < max_timeout:
            try:
                response = await asyncio.wait_for(self.websocket.recv(), timeout=2)
                data = json.loads(response)
                
                event_type = data.get("event")
                content = data.get("content", "")
                
                if event_type == "agent.thinking":
                    print(f"   💭 思考中...")
                elif event_type == "agent.tool_call":
                    tool_name = data.get("metadata", {}).get("tool", "unknown")
                    print(f"   🔧 调用工具: {tool_name}")
                elif event_type == "agent.tool_result":
                    status = data.get("metadata", {}).get("status", "unknown")
                    print(f"   📋 工具结果 ({status})")
                elif event_type == "agent.final_answer":
                    print(f"   ✨ 最终回答: {content}")
                    break
                elif event_type == "agent.error":
                    print(f"   ❌ 错误: {content}")
                    break
                elif event_type.startswith("agent."):
                    print(f"   📨 {event_type}: {content[:100]}")
                    
            except asyncio.TimeoutError:
                timeout_counter += 2
                if timeout_counter % 4 == 0:  # 每4秒打印一次等待
                    print(f"   ⏳ 等待中... ({timeout_counter}/{max_timeout}s)")
                    
        if timeout_counter >= max_timeout:
            print(f"   ⏰ 等待响应超时")
    
    async def test_multiturn_conversation(self):
        """测试多轮对话"""
        test_conversations = [
            "北京今天天气怎么样？",
            "上海今天天气如何？",  # 测试多轮天气查询
            "请告诉我北京的基本信息",  # 切换到城市信息查询
        ]
        
        for i, message in enumerate(test_conversations, 1):
            print(f"\n{'='*50}")
            print(f"第 {i} 轮对话")
            print(f"{'='*50}")
            await self.send_message(message)
            await asyncio.sleep(0.5)  # 给agent时间完成处理
            
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            print("\n🔌 连接已关闭")


async def main():
    """主测试函数"""
    tester = WebSocketTester()
    
    try:
        await tester.connect()
        await tester.create_session()
        await tester.test_multiturn_conversation()
    except Exception as e:
        print(f"❌ 测试出错: {e}")
    finally:
        await tester.close()


if __name__ == "__main__":
    print("🧪 开始多轮对话测试")
    asyncio.run(main())