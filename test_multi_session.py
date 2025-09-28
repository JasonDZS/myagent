#!/usr/bin/env python3
"""测试WebSocket服务器的多会话并发支持"""

import asyncio
import json
import websockets
import time


class WebSocketTestClient:
    def __init__(self, client_id: str, uri: str = "ws://localhost:8889"):
        self.client_id = client_id
        self.uri = uri
        self.websocket = None
        self.session_id = None
        self.messages_received = []
        
    async def connect(self):
        """连接到WebSocket服务器"""
        self.websocket = await websockets.connect(self.uri)
        print(f"[{self.client_id}] ✅ 连接成功")
        
        # 等待连接确认
        message = await self.websocket.recv()
        data = json.loads(message)
        print(f"[{self.client_id}] 📨 连接确认: {data['event']}")
        
    async def create_session(self):
        """创建新会话"""
        create_message = {"event": "user.create_session"}
        await self.websocket.send(json.dumps(create_message))
        
        # 等待会话创建确认
        message = await self.websocket.recv()
        data = json.loads(message)
        self.session_id = data.get("session_id")
        print(f"[{self.client_id}] 📨 会话创建: {self.session_id}")
        
    async def send_message(self, content: str):
        """发送用户消息"""
        message = {
            "event": "user.message",
            "session_id": self.session_id,
            "content": content
        }
        await self.websocket.send(json.dumps(message))
        print(f"[{self.client_id}] 📤 发送: {content}")
        
    async def listen_for_final_answer(self, timeout: float = 30.0):
        """监听最终答案"""
        start_time = time.time()
        try:
            while time.time() - start_time < timeout:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                data = json.loads(message)
                self.messages_received.append(data)
                
                event_type = data.get('event')
                content = data.get('content', '')
                
                if event_type == 'agent.final_answer':
                    elapsed = time.time() - start_time
                    print(f"[{self.client_id}] ✅ 收到最终答案 (用时 {elapsed:.1f}s): {content[:100]}...")
                    return True, elapsed
                elif event_type in ['agent.error', 'agent.interrupted']:
                    print(f"[{self.client_id}] ❌ 收到错误: {content}")
                    return False, time.time() - start_time
                elif event_type == 'system.heartbeat':
                    continue  # 忽略心跳
                    
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            print(f"[{self.client_id}] ⏰ 等待超时 ({elapsed:.1f}s)")
            return False, elapsed
            
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            print(f"[{self.client_id}] 🔌 连接已关闭")


async def test_client(client_id: str, query: str, delay: float = 0):
    """测试单个客户端"""
    if delay > 0:
        await asyncio.sleep(delay)
        
    client = WebSocketTestClient(client_id)
    
    try:
        await client.connect()
        await client.create_session()
        
        start_time = time.time()
        await client.send_message(query)
        
        success, elapsed = await client.listen_for_final_answer()
        
        return {
            'client_id': client_id,
            'success': success,
            'elapsed_time': elapsed,
            'start_time': start_time,
            'messages_count': len(client.messages_received)
        }
        
    except Exception as e:
        print(f"[{client_id}] ❌ 测试失败: {e}")
        return {
            'client_id': client_id,
            'success': False,
            'elapsed_time': 0,
            'error': str(e)
        }
    finally:
        await client.close()


async def test_multi_session_concurrent():
    """测试多会话并发"""
    print("🧪 测试WebSocket服务器多会话并发支持\n")
    
    # 测试场景：3个客户端同时发送不同的查询
    test_cases = [
        ("客户端A", "北京天气怎么样？", 0),
        ("客户端B", "上海的城市信息", 0.1),  # 稍微延迟启动
        ("客户端C", "广州天气如何？", 0.2),   # 再稍微延迟启动
    ]
    
    print("="*60)
    print("同时启动多个客户端测试并发处理能力")
    print("="*60)
    
    # 创建并发任务
    tasks = []
    for client_id, query, delay in test_cases:
        task = asyncio.create_task(test_client(client_id, query, delay))
        tasks.append(task)
    
    # 等待所有任务完成
    start_time = time.time()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_time = time.time() - start_time
    
    # 分析结果
    print("\n" + "="*60)
    print("测试结果分析")
    print("="*60)
    
    successful_clients = 0
    total_elapsed = 0
    
    for result in results:
        if isinstance(result, Exception):
            print(f"❌ 任务异常: {result}")
            continue
            
        client_id = result['client_id']
        success = result['success']
        elapsed = result['elapsed_time']
        
        if success:
            successful_clients += 1
            total_elapsed += elapsed
            print(f"✅ {client_id}: 成功 (用时 {elapsed:.1f}s, 收到 {result['messages_count']} 条消息)")
        else:
            error = result.get('error', '未知错误')
            print(f"❌ {client_id}: 失败 - {error}")
    
    print(f"\n📊 总体统计:")
    print(f"   总测试时间: {total_time:.1f}s")
    print(f"   成功客户端: {successful_clients}/{len(test_cases)}")
    
    if successful_clients > 0:
        avg_response_time = total_elapsed / successful_clients
        print(f"   平均响应时间: {avg_response_time:.1f}s")
    
    # 判断并发支持情况
    print(f"\n🎯 并发支持评估:")
    
    if successful_clients == len(test_cases):
        print("✅ 多会话并发支持正常")
        if total_time < (total_elapsed / successful_clients) * 1.5:
            print("✅ 并发性能良好 - 总时间明显少于串行处理时间")
        else:
            print("⚠️ 并发性能一般 - 可能存在阻塞")
    elif successful_clients > 0:
        print("⚠️ 部分会话并发成功，可能存在资源竞争")
    else:
        print("❌ 多会话并发支持存在问题")


async def main():
    """主函数"""
    try:
        await test_multi_session_concurrent()
    except Exception as e:
        print(f"❌ 测试失败: {e}")
    
    print("\n🏁 多会话并发测试完成")


if __name__ == "__main__":
    asyncio.run(main())