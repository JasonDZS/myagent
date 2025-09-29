"""Data repository for WebSocket management system."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from myagent.logger import logger
from .models import (
    AgentService,
    ServiceConfig,
    ServiceStats,
    RoutingRule,
    HealthCheckResult,
    ServiceStatus,
    HealthStatus,
)


class ServiceRepository:
    """Repository for persisting service data."""
    
    def __init__(self, db_path: str = "agent_manager.db"):
        self.db_path = Path(db_path)
        self._init_database()
    
    def _init_database(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    service_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    host TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    endpoint TEXT,
                    tags TEXT,  -- JSON array
                    agent_type TEXT,
                    version TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    last_health_check TEXT,
                    error_message TEXT,
                    restart_count INTEGER DEFAULT 0,
                    config TEXT NOT NULL,  -- JSON
                    stats TEXT NOT NULL   -- JSON
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS routing_rules (
                    rule_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    priority INTEGER NOT NULL,
                    enabled BOOLEAN NOT NULL,
                    conditions TEXT,  -- JSON array
                    target_strategy TEXT NOT NULL,
                    target_services TEXT,  -- JSON array
                    target_tags TEXT,  -- JSON array
                    weight INTEGER DEFAULT 1,
                    fallback_strategy TEXT,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    status TEXT NOT NULL,
                    response_time_ms REAL NOT NULL,
                    checks TEXT,  -- JSON
                    error_message TEXT,
                    error_details TEXT,  -- JSON
                    FOREIGN KEY (service_id) REFERENCES services (service_id)
                )
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_services_name ON services (name)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_services_status ON services (status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_routing_rules_priority ON routing_rules (priority)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_health_checks_service_timestamp ON health_checks (service_id, timestamp)")
            
            conn.commit()
    
    def save_service(self, service: AgentService) -> bool:
        """Save or update a service."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO services (
                        service_id, name, description, host, port, endpoint,
                        tags, agent_type, version, status, created_at, started_at,
                        last_health_check, error_message, restart_count, config, stats
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    service.service_id,
                    service.name,
                    service.description,
                    service.host,
                    service.port,
                    service.endpoint,
                    json.dumps(list(service.tags)),
                    service.agent_type,
                    service.version,
                    service.status.value,
                    service.created_at.isoformat(),
                    service.started_at.isoformat() if service.started_at else None,
                    service.last_health_check.isoformat() if service.last_health_check else None,
                    service.error_message,
                    service.restart_count,
                    service.config.model_dump_json(),
                    service.stats.model_dump_json(),
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save service {service.name}: {e}")
            return False
    
    def get_service(self, service_id: str) -> Optional[AgentService]:
        """Get service by ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM services WHERE service_id = ?", (service_id,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_service(row)
        except Exception as e:
            logger.error(f"Failed to get service {service_id}: {e}")
        return None
    
    def get_service_by_name(self, name: str) -> Optional[AgentService]:
        """Get service by name."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM services WHERE name = ?", (name,)
                )
                row = cursor.fetchone()
                if row:
                    return self._row_to_service(row)
        except Exception as e:
            logger.error(f"Failed to get service by name {name}: {e}")
        return None
    
    def list_services(
        self, 
        status: Optional[ServiceStatus] = None,
        tags: Optional[List[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[AgentService]:
        """List services with optional filters."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM services WHERE 1=1"
                params = []
                
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                
                query += " ORDER BY created_at DESC"
                
                if limit:
                    query += " LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                
                cursor = conn.execute(query, params)
                services = []
                
                for row in cursor.fetchall():
                    service = self._row_to_service(row)
                    if service:
                        # Filter by tags if specified
                        if tags and not any(tag in service.tags for tag in tags):
                            continue
                        services.append(service)
                
                return services
        except Exception as e:
            logger.error(f"Failed to list services: {e}")
            return []
    
    def delete_service(self, service_id: str) -> bool:
        """Delete a service."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM services WHERE service_id = ?", (service_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to delete service {service_id}: {e}")
            return False
    
    def save_routing_rule(self, rule: RoutingRule) -> bool:
        """Save or update a routing rule."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO routing_rules (
                        rule_id, name, priority, enabled, conditions,
                        target_strategy, target_services, target_tags,
                        weight, fallback_strategy, description,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    rule.rule_id,
                    rule.name,
                    rule.priority,
                    rule.enabled,
                    json.dumps([c.model_dump() for c in rule.conditions]),
                    rule.target_strategy.value,
                    json.dumps(rule.target_services),
                    json.dumps(rule.target_tags),
                    rule.weight,
                    rule.fallback_strategy.value if rule.fallback_strategy else None,
                    rule.description,
                    rule.created_at.isoformat(),
                    rule.updated_at.isoformat(),
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save routing rule {rule.name}: {e}")
            return False
    
    def get_routing_rules(self, enabled_only: bool = True) -> List[RoutingRule]:
        """Get routing rules, ordered by priority."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM routing_rules"
                if enabled_only:
                    query += " WHERE enabled = 1"
                query += " ORDER BY priority ASC"
                
                cursor = conn.execute(query)
                rules = []
                
                for row in cursor.fetchall():
                    rule = self._row_to_routing_rule(row)
                    if rule:
                        rules.append(rule)
                
                return rules
        except Exception as e:
            logger.error(f"Failed to get routing rules: {e}")
            return []
    
    def save_health_check(self, result: HealthCheckResult) -> bool:
        """Save health check result."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO health_checks (
                        service_id, timestamp, status, response_time_ms,
                        checks, error_message, error_details
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result.service_id,
                    result.timestamp.isoformat(),
                    result.status.value,
                    result.response_time_ms,
                    json.dumps({k: v.model_dump() for k, v in result.checks.items()}),
                    result.error_message,
                    json.dumps(result.error_details) if result.error_details else None,
                ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Failed to save health check for {result.service_id}: {e}")
            return False
    
    def get_health_history(
        self, 
        service_id: str, 
        limit: int = 100
    ) -> List[HealthCheckResult]:
        """Get health check history for a service."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM health_checks 
                    WHERE service_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (service_id, limit))
                
                results = []
                for row in cursor.fetchall():
                    result = self._row_to_health_check(row)
                    if result:
                        results.append(result)
                
                return results
        except Exception as e:
            logger.error(f"Failed to get health history for {service_id}: {e}")
            return []
    
    def _row_to_service(self, row) -> Optional[AgentService]:
        """Convert database row to AgentService."""
        try:
            (service_id, name, description, host, port, endpoint, tags_json,
             agent_type, version, status, created_at, started_at, last_health_check,
             error_message, restart_count, config_json, stats_json) = row
            
            return AgentService(
                service_id=service_id,
                name=name,
                description=description or "",
                host=host,
                port=port,
                endpoint=endpoint,
                tags=set(json.loads(tags_json or "[]")),
                agent_type=agent_type,
                version=version,
                status=ServiceStatus(status),
                created_at=datetime.fromisoformat(created_at),
                started_at=datetime.fromisoformat(started_at) if started_at else None,
                last_health_check=datetime.fromisoformat(last_health_check) if last_health_check else None,
                error_message=error_message,
                restart_count=restart_count,
                config=ServiceConfig.model_validate_json(config_json),
                stats=ServiceStats.model_validate_json(stats_json),
            )
        except Exception as e:
            logger.error(f"Failed to convert row to service: {e}")
            return None
    
    def _row_to_routing_rule(self, row) -> Optional[RoutingRule]:
        """Convert database row to RoutingRule."""
        try:
            from .models import RoutingCondition, RoutingStrategy
            
            (rule_id, name, priority, enabled, conditions_json, target_strategy,
             target_services_json, target_tags_json, weight, fallback_strategy,
             description, created_at, updated_at) = row
            
            conditions = []
            if conditions_json:
                for cond_data in json.loads(conditions_json):
                    conditions.append(RoutingCondition.model_validate(cond_data))
            
            return RoutingRule(
                rule_id=rule_id,
                name=name,
                priority=priority,
                enabled=bool(enabled),
                conditions=conditions,
                target_strategy=RoutingStrategy(target_strategy),
                target_services=json.loads(target_services_json or "[]"),
                target_tags=json.loads(target_tags_json or "[]"),
                weight=weight,
                fallback_strategy=RoutingStrategy(fallback_strategy) if fallback_strategy else None,
                description=description or "",
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at),
            )
        except Exception as e:
            logger.error(f"Failed to convert row to routing rule: {e}")
            return None
    
    def _row_to_health_check(self, row) -> Optional[HealthCheckResult]:
        """Convert database row to HealthCheckResult."""
        try:
            from .models import CheckResult
            
            (_, service_id, timestamp, status, response_time_ms, checks_json,
             error_message, error_details_json) = row
            
            checks = {}
            if checks_json:
                checks_data = json.loads(checks_json)
                for name, check_data in checks_data.items():
                    checks[name] = CheckResult.model_validate(check_data)
            
            return HealthCheckResult(
                service_id=service_id,
                timestamp=datetime.fromisoformat(timestamp),
                status=HealthStatus(status),
                response_time_ms=response_time_ms,
                checks=checks,
                error_message=error_message,
                error_details=json.loads(error_details_json) if error_details_json else None,
            )
        except Exception as e:
            logger.error(f"Failed to convert row to health check: {e}")
            return None