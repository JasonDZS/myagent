# 连接路由策略设计

## 概述

连接路由策略负责决定客户端连接应该转发到哪个智能体服务实例。不同的策略适用于不同的场景和需求。

## 1. 基础路由策略

### 1.1 轮询 (Round Robin)

**原理**: 按顺序依次将连接分配给可用的服务实例。

**实现**:
```python
class RoundRobinRouter:
    def __init__(self):
        self.current_index = 0
    
    def route(self, services: List[AgentService]) -> Optional[AgentService]:
        healthy_services = [s for s in services if s.status == "running"]
        if not healthy_services:
            return None
        
        service = healthy_services[self.current_index % len(healthy_services)]
        self.current_index += 1
        return service
```

**优点**:
- 简单易实现
- 负载分配均匀
- 无状态，易于扩展

**缺点**:
- 不考虑服务负载差异
- 不适合服务性能差异较大的场景

**适用场景**:
- 服务实例性能相近
- 对延迟要求不高
- 简单的负载均衡需求

### 1.2 最少连接 (Least Connections)

**原理**: 将连接分配给当前连接数最少的服务实例。

**实现**:
```python
class LeastConnectionsRouter:
    def route(self, services: List[AgentService]) -> Optional[AgentService]:
        healthy_services = [s for s in services 
                          if s.status == "running" and s.stats.active_connections < s.config.max_sessions]
        if not healthy_services:
            return None
        
        return min(healthy_services, key=lambda s: s.stats.active_connections)
```

**优点**:
- 动态负载均衡
- 适应服务处理能力差异
- 避免过载

**缺点**:
- 需要维护连接计数状态
- 计算开销稍大

**适用场景**:
- 会话持续时间差异较大
- 服务处理能力不同
- 对响应时间敏感

### 1.3 加权随机 (Weighted Random)

**原理**: 根据服务权重随机选择，权重高的服务被选中的概率更大。

**实现**:
```python
import random
from typing import List, Optional

class WeightedRandomRouter:
    def route(self, services: List[AgentService]) -> Optional[AgentService]:
        healthy_services = [(s, s.config.weight) for s in services 
                          if s.status == "running"]
        if not healthy_services:
            return None
        
        total_weight = sum(weight for _, weight in healthy_services)
        if total_weight == 0:
            return random.choice([s for s, _ in healthy_services])
        
        rand_val = random.uniform(0, total_weight)
        current_weight = 0
        
        for service, weight in healthy_services:
            current_weight += weight
            if rand_val <= current_weight:
                return service
        
        return healthy_services[-1][0]  # fallback
```

**配置权重**:
```json
{
    "service_id": "high-perf-agent",
    "weight": 10
},
{
    "service_id": "standard-agent", 
    "weight": 5
}
```

**优点**:
- 支持服务差异化
- 可以基于性能调整权重
- 随机性避免热点

**缺点**:
- 需要配置和调优权重
- 不能实时反映负载状态

**适用场景**:
- 服务性能差异明显
- 需要差异化流量分配
- 有历史性能数据支撑

## 2. 高级路由策略

### 2.1 基于哈希 (Hash-based)

**原理**: 根据客户端标识（IP、用户ID等）计算哈希值，确保相同客户端总是路由到相同服务。

**实现**:
```python
import hashlib
from typing import Dict, Any

class HashBasedRouter:
    def route(self, services: List[AgentService], 
             client_info: Dict[str, Any]) -> Optional[AgentService]:
        healthy_services = [s for s in services if s.status == "running"]
        if not healthy_services:
            return None
        
        # 使用客户端IP作为哈希键 (也可以使用用户ID等)
        hash_key = client_info.get("client_ip", "unknown")
        hash_value = int(hashlib.md5(hash_key.encode()).hexdigest(), 16)
        
        index = hash_value % len(healthy_services)
        return healthy_services[index]
```

**优点**:
- 会话亲和性，同一客户端总是连接到同一服务
- 有助于缓存和状态管理
- 分布相对均匀

**缺点**:
- 服务变更时会导致重新哈希
- 可能出现负载不均衡
- 不适合无状态服务

**适用场景**:
- 需要会话亲和性
- 服务有本地状态或缓存
- 客户端数量相对稳定

### 2.2 基于标签 (Tag-based)

**原理**: 根据客户端请求的标签或服务特征进行路由匹配。

**实现**:
```python
class TagBasedRouter:
    def route(self, services: List[AgentService], 
             required_tags: Set[str]) -> Optional[AgentService]:
        # 筛选包含所有必需标签的服务
        matching_services = []
        for service in services:
            if (service.status == "running" and 
                required_tags.issubset(service.tags)):
                matching_services.append(service)
        
        if not matching_services:
            return None
        
        # 在匹配的服务中使用最少连接策略
        return min(matching_services, 
                  key=lambda s: s.stats.active_connections)
```

**标签示例**:
```python
# 服务标签
weather_agent.tags = {"weather", "information", "real-time"}
finance_agent.tags = {"finance", "analysis", "data"}
premium_agent.tags = {"premium", "high-performance", "weather"}

# 客户端请求
required_tags = {"weather", "premium"}  # 会路由到 premium_agent
```

**优点**:
- 灵活的服务分类和匹配
- 支持多维度路由决策
- 易于扩展和管理

**缺点**:
- 配置复杂度较高
- 需要合理的标签设计
- 可能无法找到匹配服务

**适用场景**:
- 多类型智能体服务
- 需要功能导向的路由
- 服务具有明确的特征分类

### 2.3 性能导向 (Performance-based)

**原理**: 根据服务的实时性能指标进行路由选择。

**实现**:
```python
class PerformanceBasedRouter:
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or {
            "response_time": 0.4,
            "cpu_usage": 0.3, 
            "memory_usage": 0.2,
            "error_rate": 0.1
        }
    
    def calculate_score(self, service: AgentService) -> float:
        """计算服务性能评分，分数越高越好"""
        stats = service.stats
        
        # 响应时间评分 (越低越好，转换为0-100分)
        response_score = max(0, 100 - stats.avg_response_time_ms / 10)
        
        # CPU使用率评分 (越低越好)  
        cpu_score = max(0, 100 - stats.cpu_usage_percent)
        
        # 内存使用率评分 (越低越好)
        memory_score = max(0, 100 - (stats.memory_usage_mb / 1024) * 100)
        
        # 错误率评分 (越低越好)
        error_score = max(0, 100 - stats.error_rate * 100)
        
        # 加权总分
        total_score = (
            response_score * self.weights["response_time"] +
            cpu_score * self.weights["cpu_usage"] +
            memory_score * self.weights["memory_usage"] + 
            error_score * self.weights["error_rate"]
        )
        
        return total_score
    
    def route(self, services: List[AgentService]) -> Optional[AgentService]:
        healthy_services = [s for s in services if s.status == "running"]
        if not healthy_services:
            return None
        
        # 选择评分最高的服务
        return max(healthy_services, key=self.calculate_score)
```

**优点**:
- 动态适应服务性能变化
- 自动避开高负载服务
- 提升整体系统性能

**缺点**:
- 需要实时性能监控
- 计算复杂度较高
- 可能导致负载震荡

**适用场景**:
- 对性能要求极高
- 服务负载变化较大
- 有完善的监控系统

## 3. 复合路由策略

### 3.1 多级路由

**原理**: 先按照某种条件进行粗筛，再在筛选结果中应用细粒度策略。

**实现**:
```python
class MultiLevelRouter:
    def __init__(self):
        self.tag_router = TagBasedRouter()
        self.performance_router = PerformanceBasedRouter()
    
    def route(self, services: List[AgentService], 
             required_tags: Set[str]) -> Optional[AgentService]:
        # 第一级：按标签筛选
        tag_matched = [s for s in services 
                      if required_tags.issubset(s.tags) and s.status == "running"]
        
        if not tag_matched:
            return None
        
        # 第二级：在匹配的服务中选择性能最好的
        return self.performance_router.route(tag_matched)
```

### 3.2 故障转移路由

**原理**: 主要策略失败时，自动切换到备用策略。

**实现**:
```python
class FallbackRouter:
    def __init__(self, primary_router, fallback_router):
        self.primary_router = primary_router
        self.fallback_router = fallback_router
    
    def route(self, services: List[AgentService], **kwargs) -> Optional[AgentService]:
        # 尝试主要策略
        result = self.primary_router.route(services, **kwargs)
        if result:
            return result
        
        # 主要策略失败，使用备用策略
        return self.fallback_router.route(services, **kwargs)
```

## 4. 路由规则引擎

### 4.1 规则定义

```json
{
    "rules": [
        {
            "id": "vip-user-routing",
            "priority": 10,
            "name": "VIP用户专用路由",
            "conditions": [
                {
                    "field": "header.x-user-tier",
                    "operator": "equals",
                    "value": "vip"
                }
            ],
            "target": {
                "strategy": "performance_based",
                "filters": {
                    "tags": ["premium", "high-performance"],
                    "min_cpu_percent": 80
                }
            }
        },
        {
            "id": "region-based-routing", 
            "priority": 20,
            "name": "地区路由",
            "conditions": [
                {
                    "field": "client_ip",
                    "operator": "ip_in_range",
                    "value": "192.168.1.0/24"
                }
            ],
            "target": {
                "strategy": "least_connections",
                "filters": {
                    "tags": ["asia-pacific"]
                }
            }
        },
        {
            "id": "default-routing",
            "priority": 100,
            "name": "默认路由",
            "conditions": [],
            "target": {
                "strategy": "round_robin"
            }
        }
    ]
}
```

### 4.2 规则引擎实现

```python
class RoutingRuleEngine:
    def __init__(self, rules: List[RoutingRule]):
        # 按优先级排序规则
        self.rules = sorted(rules, key=lambda r: r.priority)
        self.routers = {
            "round_robin": RoundRobinRouter(),
            "least_connections": LeastConnectionsRouter(),
            "weighted_random": WeightedRandomRouter(),
            "hash_based": HashBasedRouter(),
            "tag_based": TagBasedRouter(),
            "performance_based": PerformanceBasedRouter()
        }
    
    def route(self, services: List[AgentService], 
             connection_info: ConnectionInfo) -> Optional[AgentService]:
        # 遍历规则，找到第一个匹配的
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            if self._matches_conditions(rule.conditions, connection_info):
                # 应用筛选条件
                filtered_services = self._apply_filters(services, rule.target_filters)
                
                # 执行路由策略
                router = self.routers.get(rule.target_strategy)
                if router:
                    result = router.route(filtered_services, **rule.target_params)
                    if result:
                        return result
        
        return None
    
    def _matches_conditions(self, conditions: List[RoutingCondition], 
                           connection_info: ConnectionInfo) -> bool:
        """检查连接信息是否匹配所有条件"""
        for condition in conditions:
            if not self._evaluate_condition(condition, connection_info):
                return False
        return True
    
    def _evaluate_condition(self, condition: RoutingCondition, 
                           connection_info: ConnectionInfo) -> bool:
        """评估单个条件"""
        field_value = self._get_field_value(condition.field, connection_info)
        
        if condition.operator == "equals":
            return field_value == condition.value
        elif condition.operator == "contains":
            return condition.value in str(field_value)
        elif condition.operator == "starts_with":
            return str(field_value).startswith(condition.value)
        # ... 更多操作符实现
        
        return False
```

## 5. 路由监控和优化

### 5.1 路由性能指标

- **路由延迟**: 从接收连接到选择服务的时间
- **路由成功率**: 成功路由的连接比例
- **负载均衡度**: 各服务负载分布的均衡程度
- **故障转移次数**: 主路由失败转用备用路由的次数

### 5.2 自适应路由

```python
class AdaptiveRouter:
    def __init__(self):
        self.performance_history = {}
        self.adaptation_threshold = 0.1  # 10% 性能差异触发调整
    
    def route(self, services: List[AgentService]) -> Optional[AgentService]:
        # 收集性能数据
        self._collect_performance_data(services)
        
        # 检查是否需要调整路由策略
        if self._should_adapt():
            self._adapt_strategy()
        
        # 执行路由
        return self._execute_current_strategy(services)
    
    def _should_adapt(self) -> bool:
        """判断是否应该调整路由策略"""
        # 基于历史性能数据判断
        pass
    
    def _adapt_strategy(self):
        """自适应调整路由策略"""
        # 根据性能反馈调整策略参数
        pass
```

### 5.3 A/B 测试路由

```python
class ABTestRouter:
    def __init__(self, strategy_a, strategy_b, split_ratio=0.5):
        self.strategy_a = strategy_a
        self.strategy_b = strategy_b
        self.split_ratio = split_ratio
        
    def route(self, services: List[AgentService], 
             connection_info: ConnectionInfo) -> Optional[AgentService]:
        # 基于连接ID决定使用哪个策略
        hash_val = hash(connection_info.connection_id)
        use_strategy_a = (hash_val % 100) < (self.split_ratio * 100)
        
        strategy = self.strategy_a if use_strategy_a else self.strategy_b
        result = strategy.route(services)
        
        # 记录路由结果用于分析
        self._log_routing_result(use_strategy_a, result, connection_info)
        
        return result
```

通过这种设计，可以灵活组合不同的路由策略，满足各种复杂的业务需求，并支持动态调整和优化。