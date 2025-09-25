#!/usr/bin/env python3
"""测试单个天气查询"""

import asyncio
import json
import websockets


async def test_single_weather():
    """测试单个天气查询"""
    uri = "ws://localhost:8889"
    
    try:
        print(f"🔌 连接到 {uri}")
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            print(f"📨 连接响应: {data.get('event')}")
            
            # 创建会话
            create_msg = {
                "event": "user.create_session",
                "content": "test weather session"
            }
            await websocket.send(json.dumps(create_msg))
            
            # 等待会话创建响应
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            session_data = json.loads(response)
            
            if session_data.get("event") == "agent.session_created":
                session_id = session_data.get("session_id")
                print(f"✅ 会话创建成功: {session_id[:8]}...")
                
                # 发送天气查询
                message = {
                    "event": "user.message",
                    "session_id": session_id,
                    "content": "北京今天天气怎么样？"
                }
                print("👤 发送消息: 北京今天天气怎么样？")
                await websocket.send(json.dumps(message))
                
                # 等待完整响应流
                print("🤖 Agent响应:")
                timeout_counter = 0
                max_timeout = 30  # 30秒总超时
                
                while timeout_counter < max_timeout:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2)
                        data = json.loads(response)
                        event_type = data.get("event")
                        content = data.get("content", "")
                        
                        if event_type == "agent.thinking":
                            print(f"   💭 思考中...")
                        elif event_type == "agent.tool_call":
                            tool = data.get("metadata", {}).get("tool", "unknown")
                            print(f"   🔧 调用工具: {tool}")
                        elif event_type == "agent.tool_result":
                            status = data.get("metadata", {}).get("status", "unknown")
                            print(f"   📋 工具结果 ({status})")
                        elif event_type == "agent.final_answer":
                            print(f"   ✨ 最终回答: {content}")
                            print("✅ 测试成功!")
                            return
                        elif event_type == "agent.error":
                            print(f"   ❌ Agent错误: {content}")
                            return
                        else:
                            print(f"   📨 {event_type}: {content[:100]}")
                            
                    except asyncio.TimeoutError:
                        timeout_counter += 2
                        print(f"   ⏳ 等待中... ({timeout_counter}/{max_timeout}s)")
                        
                print("⏰ 响应超时")
            else:
                print(f"❌ 会话创建失败: {session_data}")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_single_weather())