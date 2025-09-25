#!/usr/bin/env python3
"""简单的WebSocket连接测试"""

import asyncio
import json
import websockets


async def test_basic_connection():
    """测试基本连接和会话创建"""
    uri = "ws://localhost:8889"
    
    try:
        print(f"🔌 连接到 {uri}")
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            data = json.loads(response)
            print(f"📨 连接响应: {data}")
            
            # 创建会话
            create_msg = {
                "event": "user.create_session",
                "content": "test session"
            }
            print("🆕 创建会话")
            await websocket.send(json.dumps(create_msg))
            
            # 等待会话创建响应
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            session_data = json.loads(response)
            print(f"📨 会话响应: {session_data}")
            
            if session_data.get("event") == "agent.session_created":
                session_id = session_data.get("session_id")
                print(f"✅ 会话创建成功: {session_id}")
                
                # 发送简单消息
                message = {
                    "event": "user.message",
                    "session_id": session_id,
                    "content": "你好"
                }
                print("👤 发送消息: 你好")
                await websocket.send(json.dumps(message))
                
                # 等待响应
                print("🤖 等待响应...")
                timeout = 30  # 30秒超时
                try:
                    while timeout > 0:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2)
                        data = json.loads(response)
                        event_type = data.get("event")
                        content = data.get("content", "")
                        
                        print(f"   📨 {event_type}: {content}")
                        
                        if event_type == "agent.final_answer":
                            print("✅ 收到最终回答，测试成功!")
                            break
                        elif event_type == "agent.error":
                            print(f"❌ Agent错误: {content}")
                            break
                        
                        timeout -= 2
                        
                    if timeout <= 0:
                        print("⏰ 等待响应超时")
                        
                except asyncio.TimeoutError:
                    print("⏰ 接收消息超时")
            else:
                print(f"❌ 会话创建失败: {session_data}")
                
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_basic_connection())