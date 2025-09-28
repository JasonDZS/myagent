#!/usr/bin/env python3
"""简化的多会话并发测试"""

import asyncio
import json
import websockets
import time


async def test_single_client(client_id: str, query: str):
    """测试单个客户端"""
    uri = "ws://localhost:8889"
    
    print(f"[{client_id}] 开始连接...")
    
    try:
        async with websockets.connect(uri) as websocket:
            # 等待连接确认
            message = await websocket.recv()
            data = json.loads(message)
            print(f"[{client_id}] ✅ 连接成功: {data['event']}")
            
            # 创建会话
            create_msg = {"event": "user.create_session"}
            await websocket.send(json.dumps(create_msg))
            
            session_response = await websocket.recv()
            session_data = json.loads(session_response)
            session_id = session_data.get("session_id")
            print(f"[{client_id}] 📨 会话创建: {session_id}")
            
            # 发送查询
            user_msg = {
                "event": "user.message",
                "session_id": session_id,
                "content": query
            }
            await websocket.send(json.dumps(user_msg))
            print(f"[{client_id}] 📤 查询发送: {query}")
            
            # 监听响应 - 只等待第一个thinking事件
            start_time = time.time()
            try:
                while True:
                    message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    data = json.loads(message)
                    event_type = data.get('event')
                    
                    if event_type == 'agent.thinking':
                        elapsed = time.time() - start_time
                        content = data.get('content', '')
                        print(f"[{client_id}] ✅ 收到thinking事件 (用时 {elapsed:.1f}s): {content[:50]}...")
                        return True, elapsed
                    elif event_type in ['agent.error', 'system.error']:
                        print(f"[{client_id}] ❌ 收到错误: {data.get('content', '')}")
                        return False, time.time() - start_time
                        
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"[{client_id}] ⏰ 等待超时 ({elapsed:.1f}s)")
                return False, elapsed
                
    except Exception as e:
        print(f"[{client_id}] ❌ 连接失败: {e}")
        return False, 0


async def test_multi_session_simple():
    """简化的多会话测试"""
    print("🧪 简化多会话并发测试\n")
    
    # 测试场景：3个客户端同时连接和查询
    test_cases = [
        ("客户端A", "北京天气"),
        ("客户端B", "上海城市信息"),
        ("客户端C", "广州天气"),
    ]
    
    print("同时启动3个客户端...")
    
    # 并发执行
    start_time = time.time()
    tasks = [test_single_client(client_id, query) for client_id, query in test_cases]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # 分析结果
    print(f"\n📊 测试结果 (总用时 {total_time:.1f}s):")
    
    successful = 0
    total_response_time = 0
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"❌ {test_cases[i][0]}: 异常 - {result}")
            continue
            
        success, response_time = result
        client_id = test_cases[i][0]
        
        if success:
            successful += 1
            total_response_time += response_time
            print(f"✅ {client_id}: 成功 (响应时间 {response_time:.1f}s)")
        else:
            print(f"❌ {client_id}: 失败")
    
    print(f"\n🎯 多会话并发支持结论:")
    
    if successful == len(test_cases):
        avg_response = total_response_time / successful
        print(f"✅ 多会话并发支持正常")
        print(f"   成功率: {successful}/{len(test_cases)}")
        print(f"   平均响应时间: {avg_response:.1f}s")
        print(f"   总测试时间: {total_time:.1f}s")
        
        if total_time < avg_response * 2:
            print(f"✅ 并发性能良好 - 总时间({total_time:.1f}s) < 串行时间估算({avg_response * len(test_cases):.1f}s)")
        else:
            print(f"⚠️ 并发性能一般")
            
    elif successful > 0:
        print(f"⚠️ 部分并发成功: {successful}/{len(test_cases)}")
    else:
        print(f"❌ 多会话并发支持有问题")


if __name__ == "__main__":
    asyncio.run(test_multi_session_simple())