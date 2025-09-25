"""WebSocket 天气助手示例 - 演示如何创建可部署的 Agent"""

import asyncio
from typing import Any, Dict
from myagent import create_react_agent
from myagent.tool.base_tool import BaseTool, ToolResult


class WeatherTool(BaseTool):
    """模拟天气查询工具"""
    
    name: str = "get_weather" 
    description: str = "获取指定城市的天气信息"
    parameters: dict = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string",
                "description": "要查询天气的城市名称"
            },
            "date": {
                "type": "string", 
                "description": "查询日期，格式：YYYY-MM-DD，留空表示今天",
                "default": "today"
            }
        },
        "required": ["city"]
    }
    
    async def execute(self, city: str, date: str = "today") -> ToolResult:
        """执行天气查询"""
        # 模拟 API 调用延迟
        await asyncio.sleep(1)
        
        # 模拟天气数据
        weather_data = {
            "北京": {"temp": "25°C", "desc": "晴朗", "humidity": "45%"},
            "上海": {"temp": "28°C", "desc": "多云", "humidity": "60%"},
            "广州": {"temp": "32°C", "desc": "阵雨", "humidity": "80%"},
            "深圳": {"temp": "30°C", "desc": "晴转多云", "humidity": "65%"},
        }
        
        if city in weather_data:
            data = weather_data[city]
            result = f"{city}的天气：{data['temp']}，{data['desc']}，湿度{data['humidity']}"
            
            if date != "today":
                result = f"{date} {result}"
                
            return ToolResult(
                output=result,
                system=f"Successfully retrieved weather for {city}"
            )
        else:
            return ToolResult(
                output=f"抱歉，暂时无法获取{city}的天气信息。请尝试北京、上海、广州或深圳。",
                system=f"Weather data not available for {city}"
            )


class CityInfoTool(BaseTool):
    """城市信息查询工具"""
    
    name: str = "get_city_info"
    description: str = "获取城市的基本信息"
    parameters: dict = {
        "type": "object",
        "properties": {
            "city": {
                "type": "string", 
                "description": "要查询信息的城市名称"
            }
        },
        "required": ["city"]
    }
    
    async def execute(self, city: str) -> ToolResult:
        """执行城市信息查询"""
        await asyncio.sleep(0.5)
        
        city_info = {
            "北京": {
                "population": "2154万",
                "area": "1.64万平方公里", 
                "description": "中华人民共和国首都，政治、文化中心"
            },
            "上海": {
                "population": "2487万",
                "area": "6340平方公里",
                "description": "中国经济、金融中心，国际化大都市"
            },
            "广州": {
                "population": "1881万", 
                "area": "7434平方公里",
                "description": "广东省会，华南地区经济中心"
            },
            "深圳": {
                "population": "1756万",
                "area": "1997平方公里", 
                "description": "经济特区，科技创新中心"
            }
        }
        
        if city in city_info:
            info = city_info[city]
            result = f"{city}信息：\n人口：{info['population']}\n面积：{info['area']}\n简介：{info['description']}"
            
            return ToolResult(
                output=result,
                system=f"Successfully retrieved city info for {city}"
            )
        else:
            return ToolResult(
                output=f"抱歉，暂时没有{city}的详细信息。",
                system=f"City info not available for {city}"
            )


# 创建 Agent 实例（必须命名为 'agent'）
agent = create_react_agent(
    name="weather-assistant",
    tools=[WeatherTool(), CityInfoTool()],
    system_prompt="""你是一个智能天气助手，可以帮助用户：
1. 查询城市天气信息 (使用 get_weather 工具)
2. 获取城市基本信息 (使用 get_city_info 工具)

请根据用户的问题，选择合适的工具来提供准确的信息。
如果用户询问天气，使用 get_weather 工具。
如果用户询问城市信息，使用 get_city_info 工具。
回答时要友好、准确，并提供有用的建议。""",
    
    next_step_prompt="根据用户的问题，选择合适的工具来获取信息，然后给出友好的回答。",
    max_steps=5,
    enable_tracing=True
)


# 可选：添加一些测试代码（仅在直接运行此文件时执行）
if __name__ == "__main__":
    async def test_agent():
        """测试 Agent 功能"""
        print("🧪 测试天气 Agent...")
        
        test_queries = [
            "北京今天天气怎么样？",
            "请告诉我上海的基本信息",
            "广州的天气如何？",
            "深圳是什么样的城市？"
        ]
        
        for query in test_queries:
            print(f"\n❓ 用户问题: {query}")
            try:
                result = await agent.arun(query)
                print(f"🤖 Agent回答: {result}")
            except Exception as e:
                print(f"❌ 执行出错: {e}")
        
        print("\n✅ 测试完成！")
    
    # 运行测试
    asyncio.run(test_agent())