# MyAgent Manager 功能测试计划

## 测试目标
验证 MyAgent WebSocket 管理系统的核心功能是否完善、稳定和可靠。

## 测试环境
- Python 3.10+
- SQLite 数据库
- WebSocket 连接支持
- 多进程环境

---

## 1. 服务注册与生命周期管理 (ServiceRegistry)

### 1.1 服务注册
- [ ] **test_register_service_success** - 成功注册新服务
  - 验证服务信息保存到数据库
  - 验证端口自动分配
  - 验证服务 ID 生成

- [ ] **test_register_duplicate_service** - 注册重复服务名称
  - 验证返回错误
  - 验证数据库中无重复记录

- [ ] **test_register_service_invalid_factory_path** - 无效的 agent_factory_path
  - 验证文件路径检查
  - 验证返回适当错误

- [ ] **test_register_service_with_specific_port** - 指定端口注册
  - 验证使用指定端口
  - 验证端口冲突检测

- [ ] **test_register_service_with_tags** - 带标签注册
  - 验证标签正确保存
  - 验证可通过标签查询

### 1.2 服务启动
- [ ] **test_start_service_success** - 成功启动服务
  - 验证进程启动
  - 验证状态更新为 RUNNING
  - 验证 started_at 时间戳
  - 验证 WebSocket 服务可访问

- [ ] **test_start_already_running_service** - 启动已运行的服务
  - 验证返回成功但不重复启动

- [ ] **test_start_nonexistent_service** - 启动不存在的服务
  - 验证返回错误

- [ ] **test_start_service_process_exits** - 进程启动后立即退出
  - 验证状态更新为 ERROR
  - 验证错误信息记录

### 1.3 服务停止
- [ ] **test_stop_service_success** - 成功停止服务
  - 验证进程终止
  - 验证状态更新为 STOPPED
  - 验证 started_at 清空

- [ ] **test_stop_service_graceful_shutdown** - 优雅停止(10秒超时)
  - 验证 terminate 信号发送
  - 验证等待进程退出

- [ ] **test_stop_service_force_kill** - 强制停止(超时后)
  - 验证 kill 信号发送
  - 验证进程最终终止

- [ ] **test_stop_already_stopped_service** - 停止已停止的服务
  - 验证返回成功

### 1.4 服务重启
- [ ] **test_restart_service_success** - 成功重启服务
  - 验证先停止再启动
  - 验证 restart_count 递增
  - 验证服务可正常使用

- [ ] **test_restart_service_with_delay** - 重启等待延迟
  - 验证停止和启动之间有1秒延迟

### 1.5 服务注销
- [ ] **test_unregister_service_success** - 成功注销服务
  - 验证服务从数据库删除
  - 验证端口释放
  - 验证运行中的服务先停止

### 1.6 端口分配
- [ ] **test_port_allocator_allocate** - 端口自动分配
  - 验证从范围 8081-9000 分配
  - 验证端口可用性检查

- [ ] **test_port_allocator_reserve_release** - 端口预留和释放
  - 验证端口预留后不可再分配
  - 验证端口释放后可再分配

- [ ] **test_port_allocator_no_available_ports** - 无可用端口
  - 验证返回 None

---

## 2. 连接路由与负载均衡 (ConnectionRouter)

### 2.1 路由策略
- [ ] **test_route_connection_round_robin** - 轮询路由
  - 验证连接依次分配到各服务
  - 验证循环分配

- [ ] **test_route_connection_least_connections** - 最少连接路由
  - 验证选择连接数最少的服务
  - 验证连接数实时更新

- [ ] **test_route_connection_weighted_random** - 加权随机路由
  - 验证基于连接数的反向权重
  - 验证随机分布

- [ ] **test_route_connection_hash_based** - 基于哈希的路由(会话亲和)
  - 验证相同 IP 路由到相同服务
  - 验证不同 IP 分散到不同服务

- [ ] **test_route_connection_tag_based** - 基于标签的路由
  - 验证根据标签过滤服务

### 2.2 路由规则匹配
- [ ] **test_routing_rule_equals** - 相等条件匹配
  - 验证 EQUALS 操作符

- [ ] **test_routing_rule_not_equals** - 不相等条件匹配
  - 验证 NOT_EQUALS 操作符

- [ ] **test_routing_rule_contains** - 包含条件匹配
  - 验证 CONTAINS 操作符

- [ ] **test_routing_rule_regex_match** - 正则表达式匹配
  - 验证 REGEX_MATCH 操作符
  - 验证大小写敏感选项

- [ ] **test_routing_rule_in_list** - 列表包含匹配
  - 验证 IN_LIST 操作符
  - 验证逗号分隔的值

- [ ] **test_routing_rule_priority** - 规则优先级
  - 验证高优先级规则先匹配
  - 验证匹配后不继续检查

- [ ] **test_routing_rule_disabled** - 禁用的规则
  - 验证禁用规则不生效

### 2.3 连接管理
- [ ] **test_register_connection** - 注册连接
  - 验证连接信息保存
  - 验证连接 ID 唯一性

- [ ] **test_unregister_connection** - 注销连接
  - 验证连接信息删除

- [ ] **test_update_connection_status** - 更新连接状态
  - 验证状态更新
  - 验证最后活动时间更新

- [ ] **test_get_service_connections** - 获取服务的所有连接
  - 验证按服务 ID 过滤

- [ ] **test_get_connection_stats** - 获取连接统计
  - 验证总连接数
  - 验证按状态分组
  - 验证按服务分组

### 2.4 边界情况
- [ ] **test_route_connection_no_available_services** - 无可用服务
  - 验证返回 None

- [ ] **test_route_connection_all_services_busy** - 所有服务繁忙
  - 验证仍能路由(选择最优)

---

## 3. 健康监控与自动重启 (HealthMonitor)

### 3.1 健康检查
- [ ] **test_check_service_health_healthy** - 健康服务检查
  - 验证 WebSocket 连通性检查
  - 验证服务状态检查
  - 验证整体状态为 HEALTHY
  - 验证响应时间记录

- [ ] **test_check_service_health_unhealthy** - 不健康服务检查
  - 验证检测到 WebSocket 连接失败
  - 验证整体状态为 UNHEALTHY
  - 验证错误信息记录

- [ ] **test_check_service_health_degraded** - 降级服务检查
  - 验证检测到连接超时
  - 验证状态为 DEGRADED

- [ ] **test_check_all_services** - 批量健康检查
  - 验证检查所有 RUNNING 和 UNHEALTHY 服务
  - 验证并发执行
  - 验证异常处理

### 3.2 健康监控循环
- [ ] **test_start_monitoring** - 启动监控
  - 验证监控任务启动
  - 验证定时检查执行

- [ ] **test_stop_monitoring** - 停止监控
  - 验证监控任务取消
  - 验证清理资源

- [ ] **test_monitoring_interval** - 监控间隔
  - 验证按指定间隔执行检查

### 3.3 健康历史
- [ ] **test_save_health_check_result** - 保存健康检查结果
  - 验证结果存储到数据库

- [ ] **test_get_service_health_history** - 获取健康历史
  - 验证按服务 ID 查询
  - 验证限制返回数量
  - 验证按时间倒序

- [ ] **test_get_health_summary** - 获取健康摘要
  - 验证统计各状态服务数量

### 3.4 自动状态更新
- [ ] **test_unhealthy_status_update** - 不健康状态自动更新
  - 验证 RUNNING 服务检测不健康后更新为 UNHEALTHY

- [ ] **test_healthy_status_recovery** - 健康状态恢复
  - 验证 UNHEALTHY 服务恢复后更新为 RUNNING

---

## 4. 自动重启机制 (AgentManager)

### 4.1 自动重启
- [ ] **test_auto_restart_on_error** - 错误时自动重启
  - 验证 ERROR 状态服务自动重启
  - 验证遵守重启延迟配置

- [ ] **test_auto_restart_on_unhealthy** - 不健康时自动重启
  - 验证 UNHEALTHY 状态服务自动重启

- [ ] **test_auto_restart_max_count** - 最大重启次数限制
  - 验证达到最大次数后停止重启
  - 验证 restart_count 正确递增

- [ ] **test_auto_restart_disabled** - 禁用自动重启
  - 验证 auto_restart=False 时不重启

- [ ] **test_auto_restart_delay** - 重启延迟
  - 验证重启前等待指定延迟

### 4.2 自动重启循环
- [ ] **test_auto_restart_loop_running** - 重启循环运行
  - 验证每30秒检查一次

- [ ] **test_auto_restart_loop_exception_handling** - 异常处理
  - 验证循环中异常不会中断监控

---

## 5. API 服务器 (APIServer)

### 5.1 服务管理接口
- [ ] **test_api_create_service** - POST /api/v1/services
  - 验证创建成功返回 200
  - 验证返回服务信息

- [ ] **test_api_list_services** - GET /api/v1/services
  - 验证列表返回
  - 验证分页参数
  - 验证状态过滤
  - 验证标签过滤

- [ ] **test_api_get_service** - GET /api/v1/services/{id}
  - 验证返回指定服务
  - 验证不存在返回 404

- [ ] **test_api_update_service** - PUT /api/v1/services/{id}
  - 验证更新服务配置
  - 验证部分更新

- [ ] **test_api_delete_service** - DELETE /api/v1/services/{id}
  - 验证删除成功
  - 验证运行中服务先停止

### 5.2 服务控制接口
- [ ] **test_api_start_service** - POST /api/v1/services/{id}/start
  - 验证启动成功返回 200

- [ ] **test_api_stop_service** - POST /api/v1/services/{id}/stop
  - 验证停止成功返回 200

- [ ] **test_api_restart_service** - POST /api/v1/services/{id}/restart
  - 验证重启成功返回 200

### 5.3 统计与监控接口
- [ ] **test_api_get_service_stats** - GET /api/v1/services/{id}/stats
  - 验证返回服务统计信息

- [ ] **test_api_check_service_health** - GET /api/v1/services/{id}/health
  - 验证返回健康检查结果
  - 验证包含详细检查项

- [ ] **test_api_get_system_stats** - GET /api/v1/stats
  - 验证返回系统级统计
  - 验证包含服务、连接、健康摘要

### 5.4 连接管理接口
- [ ] **test_api_list_connections** - GET /api/v1/connections
  - 验证返回活跃连接列表

- [ ] **test_api_disconnect_connection** - DELETE /api/v1/connections/{id}
  - 验证断开指定连接

### 5.5 路由规则接口
- [ ] **test_api_create_routing_rule** - POST /api/v1/routing/rules
  - 验证创建路由规则

- [ ] **test_api_list_routing_rules** - GET /api/v1/routing/rules
  - 验证列出路由规则
  - 验证 enabled_only 过滤

### 5.6 通用接口
- [ ] **test_api_health_check** - GET /health
  - 验证返回健康状态

- [ ] **test_api_system_info** - GET /api/v1/info
  - 验证返回系统信息

### 5.7 错误处理
- [ ] **test_api_error_handling** - 异常处理
  - 验证返回 500 错误
  - 验证错误信息格式

- [ ] **test_api_not_found** - 资源不存在
  - 验证返回 404

- [ ] **test_api_bad_request** - 无效请求
  - 验证返回 400

### 5.8 CORS
- [ ] **test_api_cors_headers** - CORS 头设置
  - 验证允许跨域请求

---

## 6. WebSocket 代理服务器 (ProxyServer)

### 6.1 连接代理
- [ ] **test_proxy_client_connection** - 客户端连接代理
  - 验证接受客户端连接
  - 验证路由到目标服务
  - 验证连接成功消息发送

- [ ] **test_proxy_bidirectional_messaging** - 双向消息转发
  - 验证客户端→服务消息转发
  - 验证服务→客户端消息转发
  - 验证消息内容完整

- [ ] **test_proxy_connection_info_extraction** - 连接信息提取
  - 验证客户端 IP 提取
  - 验证 User-Agent 提取
  - 验证请求头提取
  - 验证查询参数提取

### 6.2 连接管理
- [ ] **test_proxy_register_connection** - 注册代理连接
  - 验证连接注册到 ConnectionRouter

- [ ] **test_proxy_unregister_connection** - 注销代理连接
  - 验证连接关闭时注销

- [ ] **test_proxy_connection_activity_tracking** - 连接活动跟踪
  - 验证最后活动时间更新
  - 验证消息计数更新
  - 验证状态更新

### 6.3 错误处理
- [ ] **test_proxy_no_available_service** - 无可用服务
  - 验证返回错误消息给客户端

- [ ] **test_proxy_service_connection_failed** - 服务连接失败
  - 验证错误处理
  - 验证错误消息发送

- [ ] **test_proxy_client_disconnected** - 客户端断开
  - 验证优雅处理
  - 验证服务连接关闭

- [ ] **test_proxy_service_disconnected** - 服务断开
  - 验证优雅处理
  - 验证客户端连接关闭

### 6.4 并发连接
- [ ] **test_proxy_multiple_concurrent_connections** - 多个并发连接
  - 验证支持多客户端同时连接
  - 验证连接隔离

- [ ] **test_proxy_connection_cleanup** - 连接清理
  - 验证连接关闭后资源释放

---

## 7. 数据持久化 (Storage)

### 7.1 服务存储
- [ ] **test_save_service** - 保存服务
  - 验证服务信息持久化
  - 验证更新已存在服务

- [ ] **test_get_service** - 获取服务
  - 验证按 ID 查询

- [ ] **test_get_service_by_name** - 按名称获取服务
  - 验证名称唯一性查询

- [ ] **test_list_services_with_filters** - 列表查询带过滤
  - 验证状态过滤
  - 验证标签过滤
  - 验证分页

- [ ] **test_delete_service** - 删除服务
  - 验证从数据库删除

### 7.2 健康检查存储
- [ ] **test_save_health_check** - 保存健康检查
  - 验证检查结果持久化

- [ ] **test_get_health_history** - 获取健康历史
  - 验证按服务 ID 查询
  - 验证限制数量
  - 验证时间排序

### 7.3 路由规则存储
- [ ] **test_save_routing_rule** - 保存路由规则
  - 验证规则持久化

- [ ] **test_get_routing_rules** - 获取路由规则
  - 验证查询所有规则
  - 验证 enabled_only 过滤
  - 验证按优先级排序

### 7.4 数据库初始化
- [ ] **test_database_schema_creation** - 数据库架构创建
  - 验证表自动创建
  - 验证索引创建

---

## 8. 集成测试与端到端测试

### 8.1 完整流程测试
- [ ] **test_e2e_service_lifecycle** - 端到端服务生命周期
  1. 注册服务
  2. 启动服务
  3. 验证健康检查
  4. 停止服务
  5. 注销服务

- [ ] **test_e2e_connection_routing** - 端到端连接路由
  1. 启动多个服务
  2. 客户端连接代理
  3. 验证路由到正确服务
  4. 发送消息
  5. 验证响应
  6. 断开连接

- [ ] **test_e2e_auto_restart** - 端到端自动重启
  1. 启动服务
  2. 模拟服务崩溃
  3. 验证自动重启
  4. 验证服务恢复正常

- [ ] **test_e2e_load_balancing** - 端到端负载均衡
  1. 启动多个服务
  2. 多个客户端连接
  3. 验证负载均衡分配
  4. 验证连接统计

### 8.2 压力测试
- [ ] **test_stress_many_services** - 大量服务注册
  - 验证注册 50+ 服务
  - 验证性能

- [ ] **test_stress_many_connections** - 大量并发连接
  - 验证 100+ 并发连接
  - 验证稳定性

- [ ] **test_stress_high_message_rate** - 高消息频率
  - 验证每秒处理大量消息

### 8.3 容错测试
- [ ] **test_fault_service_crash** - 服务崩溃恢复
  - 验证服务崩溃后自动重启

- [ ] **test_fault_database_corruption** - 数据库异常处理
  - 验证数据库错误不会导致系统崩溃

- [ ] **test_fault_network_interruption** - 网络中断处理
  - 验证 WebSocket 连接中断后恢复

### 8.4 性能测试
- [ ] **test_perf_routing_latency** - 路由延迟
  - 验证路由决策时间 < 10ms

- [ ] **test_perf_health_check_overhead** - 健康检查开销
  - 验证健康检查不影响正常服务

- [ ] **test_perf_api_response_time** - API 响应时间
  - 验证 API 接口响应时间 < 100ms

---

## 9. 配置与环境测试

### 9.1 配置测试
- [ ] **test_config_custom_port_range** - 自定义端口范围
  - 验证配置不同端口范围

- [ ] **test_config_health_check_interval** - 健康检查间隔配置
  - 验证自定义检查间隔

- [ ] **test_config_auto_restart_settings** - 自动重启配置
  - 验证 max_restart_count
  - 验证 restart_delay

### 9.2 环境测试
- [ ] **test_env_database_path** - 数据库路径配置
  - 验证自定义数据库路径

- [ ] **test_env_agent_factory_environment** - Agent 环境变量
  - 验证环境变量传递给子进程

---

## 测试优先级

### P0 (必须测试 - 核心功能)
1. 服务注册、启动、停止
2. 连接路由基本策略
3. WebSocket 代理基本功能
4. API 基本接口
5. 数据持久化基本功能

### P1 (重要测试 - 关键特性)
1. 健康监控与自动重启
2. 路由规则匹配
3. 多种负载均衡策略
4. 错误处理与恢复
5. 连接管理与统计

### P2 (次要测试 - 增强功能)
1. 端到端集成测试
2. 压力测试
3. 性能测试
4. 边界情况

---

## 测试工具与框架

- **单元测试**: pytest
- **异步测试**: pytest-asyncio
- **WebSocket 测试**: websockets 库
- **HTTP API 测试**: httpx 或 requests
- **Mock/Stub**: pytest-mock, unittest.mock
- **数据库测试**: 临时 SQLite 数据库
- **覆盖率**: pytest-cov

---

## 测试报告指标

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖核心流程
- [ ] 所有 P0 测试通过
- [ ] 所有 P1 测试通过
- [ ] 性能基准达标
- [ ] 无已知严重缺陷

---

## 已知限制与待测试功能

1. **资源使用检查** - HealthMonitor._check_resource_usage 未实现
2. **路由规则更新/删除** - API 缺少 PUT/DELETE 端点
3. **连接重连机制** - 需要测试断线重连
4. **会话持久化** - 需要测试会话状态保存
5. **指标导出** - 需要测试 Prometheus/统计指标导出
6. **日志聚合** - 需要测试日志收集和查询
7. **安全认证** - 需要测试 API 认证机制
8. **限流功能** - 需要测试连接速率限制
