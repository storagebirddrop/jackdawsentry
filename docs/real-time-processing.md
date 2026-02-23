# Real-Time Processing Architecture

## Overview

Jackdaw Sentry's real-time processing architecture delivers sub-second competitive intelligence through an event-driven, stream-processing pipeline. The system leverages Redis pub/sub for event distribution, WebSocket for live updates, and advanced stream processing algorithms for real-time analytics.

## ⚡ Stream Processing Architecture

### **Event-Driven Architecture**

#### **Core Components**
```python
class StreamProcessor:
    def __init__(self):
        self.redis_client = aioredis.Redis()
        self.event_store = EventStore()
        self.aggregator = StreamAggregator()
        self.alert_manager = AlertManager()
        self.websocket_manager = WebSocketManager()
    
    async def start_processing(self):
        """Start the stream processing pipeline"""
        # Subscribe to competitive events
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("competitive_events")
        
        # Start processing loop
        asyncio.create_task(self.process_events(pubsub))
        
        # Start aggregation tasks
        asyncio.create_task(self.aggregate_metrics())
        
        # Start alert monitoring
        asyncio.create_task(self.monitor_alerts())
```

#### **Event Types and Processing**
```python
class EventType(Enum):
    BENCHMARK_COMPLETED = "benchmark_completed"
    ANOMALY_DETECTED = "anomaly_detected"
    COMPETITIVE_UPDATE = "competitive_update"
    ALERT_TRIGGERED = "alert_triggered"
    INSIGHT_GENERATED = "insight_generated"
    PERFORMANCE_METRIC = "performance_metric"

class EventProcessor:
    def __init__(self):
        self.processors = {
            EventType.BENCHMARK_COMPLETED: self.process_benchmark,
            EventType.ANOMALY_DETECTED: self.process_anomaly,
            EventType.COMPETITIVE_UPDATE: self.process_competitive_update,
            EventType.ALERT_TRIGGERED: self.process_alert,
            EventType.INSIGHT_GENERATED: self.process_insight,
            EventType.PERFORMANCE_METRIC: self.process_metric
        }
    
    async def process_event(self, event):
        """Process incoming event based on type"""
        event_type = EventType(event.get('type'))
        processor = self.processors.get(event_type)
        
        if processor:
            await processor(event)
        else:
            logger.warning(f"Unknown event type: {event_type}")
```

### **Redis Pub/Sub Implementation**

#### **Event Publishing**
```python
class EventPublisher:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.serializer = EventSerializer()
    
    async def publish_event(self, event_type, data):
        """Publish event to Redis channel"""
        event = {
            'type': event_type.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data,
            'event_id': str(uuid.uuid4())
        }
        
        serialized_event = self.serializer.serialize(event)
        
        await self.redis_client.publish(
            "competitive_events",
            serialized_event
        )
        
        # Store event for audit trail
        await self.store_event(event)
    
    async def store_event(self, event):
        """Store event in database for audit trail"""
        async with get_db_pool().acquire() as conn:
            await conn.execute("""
                INSERT INTO competitive.events 
                (event_id, event_type, timestamp, data)
                VALUES ($1, $2, $3, $4)
            """, event['event_id'], event['type'], event['timestamp'], json.dumps(event['data']))
```

#### **Event Subscription**
```python
class EventSubscriber:
    def __init__(self, redis_client):
        self.redis_client = redis_client
        self.deserializer = EventSerializer()
        self.handlers = {}
    
    def subscribe(self, event_type, handler):
        """Subscribe to specific event type"""
        if event_type not in self.handlers:
            self.handlers[event_type] = []
        self.handlers[event_type].append(handler)
    
    async def start_subscription(self):
        """Start listening for events"""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("competitive_events")
        
        async for message in pubsub.listen():
            try:
                event = self.deserializer.deserialize(message.data)
                event_type = EventType(event['type'])
                
                # Call all handlers for this event type
                for handler in self.handlers.get(event_type, []):
                    await handler(event)
                    
            except Exception as e:
                logger.error(f"Error processing event: {e}")
```

## 🔄 Real-Time Aggregation

### **Windowed Analytics**

#### **Time Window Processing**
```python
class WindowedAggregator:
    def __init__(self):
        self.windows = {}
        self.redis_client = aioredis.Redis()
    
    async def add_metric(self, metric_name, value, timestamp=None):
        """Add metric to appropriate time windows"""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Add to different window sizes
        window_sizes = ['1m', '5m', '15m', '1h', '6h', '24h']
        
        for window_size in window_sizes:
            window_key = f"metrics:{metric_name}:{window_size}"
            await self.redis_client.zadd(window_key, {timestamp.timestamp(): value})
            
            # Remove old data points
            cutoff_time = self.get_cutoff_time(window_size, timestamp)
            await self.redis_client.zremrangebyscore(window_key, 0, cutoff_time.timestamp())
    
    def get_cutoff_time(self, window_size, current_time):
        """Get cutoff time for window size"""
        durations = {
            '1m': timedelta(minutes=1),
            '5m': timedelta(minutes=5),
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '24h': timedelta(hours=24)
        }
        
        return current_time - durations[window_size]
    
    async def get_aggregated_metrics(self, metric_name, window_size, aggregation_type='avg'):
        """Get aggregated metrics for window"""
        window_key = f"metrics:{metric_name}:{window_size}"
        
        if aggregation_type == 'avg':
            # Calculate average using Redis commands
            await self.redis_client.zrange(window_key, 0, -1, withscores=True)
            # Implementation would calculate average from scores
        
        elif aggregation_type == 'sum':
            # Calculate sum
            pass
        
        elif aggregation_type == 'count':
            # Get count
            count = await self.redis_client.zcard(window_key)
            return count
        
        elif aggregation_type == 'min':
            # Get minimum
            min_result = await self.redis_client.zrange(window_key, 0, 0, withscores=True)
            return min_result[0][1] if min_result else None
        
        elif aggregation_type == 'max':
            # Get maximum
            max_result = await self.redis_client.zrange(window_key, -1, -1, withscores=True)
            return max_result[0][1] if max_result else None
```

#### **Complex Event Processing**
```python
class ComplexEventProcessor:
    def __init__(self):
        self.pattern_detector = PatternDetector()
        self.correlation_engine = CorrelationEngine()
        self.aggregator = WindowedAggregator()
    
    async def process_complex_event(self, event):
        """Process complex events with correlation"""
        # Detect patterns in event stream
        patterns = await self.pattern_detector.detect_patterns(event)
        
        # Correlate with historical events
        correlations = await self.correlation_engine.find_correlations(event)
        
        # Update aggregated metrics
        await self.update_aggregated_metrics(event)
        
        # Generate insights if patterns found
        if patterns or correlations:
            await self.generate_insights(event, patterns, correlations)
    
    async def update_aggregated_metrics(self, event):
        """Update aggregated metrics based on event"""
        if event['type'] == 'benchmark_completed':
            metrics = event['data'].get('metrics', {})
            for metric_name, value in metrics.items():
                await self.aggregator.add_metric(metric_name, value)
        
        elif event['type'] == 'anomaly_detected':
            await self.aggregator.add_metric('anomaly_count', 1)
        
        elif event['type'] == 'performance_metric':
            metric_name = event['data'].get('metric_name')
            metric_value = event['data'].get('value')
            if metric_name and metric_value:
                await self.aggregator.add_metric(metric_name, metric_value)
```

## 🌐 WebSocket Real-Time Updates

### **WebSocket Manager**
```python
class WebSocketManager:
    def __init__(self):
        self.connections = {}
        self.redis_client = aioredis.Redis()
        self.message_queue = asyncio.Queue()
    
    async def register_connection(self, websocket, user_id):
        """Register new WebSocket connection"""
        self.connections[user_id] = websocket
        logger.info(f"WebSocket connection registered for user: {user_id}")
        
        # Send initial state
        await self.send_initial_state(websocket, user_id)
    
    async def unregister_connection(self, user_id):
        """Unregister WebSocket connection"""
        if user_id in self.connections:
            del self.connections[user_id]
            logger.info(f"WebSocket connection unregistered for user: {user_id}")
    
    async def broadcast_update(self, message_type, data):
        """Broadcast update to all connected clients"""
        message = {
            'type': message_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data
        }
        
        # Send to all connected clients
        disconnected_clients = []
        
        for user_id, websocket in self.connections.items():
            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error sending to client {user_id}: {e}")
                disconnected_clients.append(user_id)
        
        # Clean up disconnected clients
        for user_id in disconnected_clients:
            await self.unregister_connection(user_id)
    
    async def send_personalized_update(self, user_id, message_type, data):
        """Send personalized update to specific user"""
        if user_id not in self.connections:
            return
        
        message = {
            'type': message_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'data': data,
            'personalized': True
        }
        
        try:
            await self.connections[user_id].send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personalized update to {user_id}: {e}")
            await self.unregister_connection(user_id)
```

### **Real-Time Dashboard Updates**
```python
class DashboardUpdater:
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.aggregator = WindowedAggregator()
        self.update_interval = 5  # seconds
    
    async def start_updates(self):
        """Start real-time dashboard updates"""
        while True:
            try:
                # Collect current metrics
                metrics = await self.collect_dashboard_metrics()
                
                # Broadcast to all connected clients
                await self.websocket_manager.broadcast_update('dashboard_update', metrics)
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in dashboard update: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def collect_dashboard_metrics(self):
        """Collect metrics for dashboard"""
        metrics = {}
        
        # Competitive parity metrics
        metrics['competitive_parity'] = await self.aggregator.get_aggregated_metrics(
            'competitive_parity', '5m', 'avg'
        )
        
        # Anomaly count
        metrics['anomaly_count'] = await self.aggregator.get_aggregated_metrics(
            'anomaly_count', '5m', 'sum'
        )
        
        # Performance metrics
        metrics['api_response_time'] = await self.aggregator.get_aggregated_metrics(
            'api_response_time', '5m', 'avg'
        )
        
        # Benchmark success rate
        total_benchmarks = await self.aggregator.get_aggregated_metrics(
            'benchmark_total', '5m', 'sum'
        )
        successful_benchmarks = await self.aggregator.get_aggregated_metrics(
            'benchmark_success', '5m', 'sum'
        )
        
        if total_benchmarks > 0:
            metrics['benchmark_success_rate'] = successful_benchmarks / total_benchmarks
        else:
            metrics['benchmark_success_rate'] = 0
        
        return metrics
```

## 🚨 Real-Time Alerting

### **Alert Detection Engine**
```python
class AlertEngine:
    def __init__(self):
        self.rules = {}
        self.conditions = {}
        self.websocket_manager = WebSocketManager()
        self.alert_store = AlertStore()
    
    def register_alert_rule(self, rule_id, rule_config):
        """Register alert rule"""
        self.rules[rule_id] = rule_config
        
        # Pre-compile conditions for performance
        self.conditions[rule_id] = self.compile_conditions(rule_config['conditions'])
    
    async def evaluate_alerts(self, metrics):
        """Evaluate alert rules against current metrics"""
        triggered_alerts = []
        
        for rule_id, rule in self.rules.items():
            if await self.evaluate_rule(rule_id, rule, metrics):
                alert = await self.create_alert(rule_id, rule, metrics)
                triggered_alerts.append(alert)
                
                # Store alert
                await self.alert_store.store_alert(alert)
                
                # Send real-time notification
                await self.send_alert_notification(alert)
        
        return triggered_alerts
    
    async def evaluate_rule(self, rule_id, rule, metrics):
        """Evaluate single alert rule"""
        conditions = self.conditions[rule_id]
        
        for condition in conditions:
            if not await self.evaluate_condition(condition, metrics):
                return False
        
        return True
    
    async def evaluate_condition(self, condition, metrics):
        """Evaluate single condition"""
        metric_name = condition['metric']
        operator = condition['operator']
        threshold = condition['threshold']
        
        if metric_name not in metrics:
            return False
        
        current_value = metrics[metric_name]
        
        if operator == 'gt':
            return current_value > threshold
        elif operator == 'lt':
            return current_value < threshold
        elif operator == 'eq':
            return abs(current_value - threshold) < 0.001
        elif operator == 'gte':
            return current_value >= threshold
        elif operator == 'lte':
            return current_value <= threshold
        else:
            return False
    
    async def create_alert(self, rule_id, rule, metrics):
        """Create alert object"""
        alert = {
            'alert_id': str(uuid.uuid4()),
            'rule_id': rule_id,
            'rule_name': rule['name'],
            'severity': rule['severity'],
            'message': self.generate_alert_message(rule, metrics),
            'metrics': metrics,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'triggered'
        }
        
        return alert
    
    async def send_alert_notification(self, alert):
        """Send real-time alert notification"""
        # Broadcast to WebSocket clients
        await self.websocket_manager.broadcast_update('alert_triggered', alert)
        
        # Send webhook notifications
        await self.send_webhook_notifications(alert)
        
        # Send email notifications for critical alerts
        if alert['severity'] in ['high', 'critical']:
            await self.send_email_notification(alert)
```

## 📊 Performance Optimization

### **Backpressure Handling**
```python
class BackpressureHandler:
    def __init__(self):
        self.queue_sizes = {}
        self.max_queue_size = 10000
        self.drop_strategy = 'oldest'  # or 'newest', 'random'
    
    async def handle_backpressure(self, queue_name, event):
        """Handle backpressure when queue is full"""
        current_size = self.queue_sizes.get(queue_name, 0)
        
        if current_size >= self.max_queue_size:
            if self.drop_strategy == 'oldest':
                # Drop oldest event
                await self.drop_oldest_event(queue_name)
            elif self.drop_strategy == 'newest':
                # Drop current event
                return False
            elif self.drop_strategy == 'random':
                # Drop random event
                await self.drop_random_event(queue_name)
        
        # Add event to queue
        await self.add_to_queue(queue_name, event)
        return True
    
    async def drop_oldest_event(self, queue_name):
        """Drop oldest event from queue"""
        queue_key = f"queue:{queue_name}"
        await self.redis_client.lpop(queue_key)
        self.queue_sizes[queue_name] = max(0, self.queue_sizes.get(queue_name, 0) - 1)
    
    async def add_to_queue(self, queue_name, event):
        """Add event to queue"""
        queue_key = f"queue:{queue_name}"
        await self.redis_client.rpush(queue_key, json.dumps(event))
        self.queue_sizes[queue_name] = self.queue_sizes.get(queue_name, 0) + 1
```

### **Caching Strategy**
```python
class RealTimeCache:
    def __init__(self):
        self.redis_client = aioredis.Redis()
        self.cache_ttl = {
            'metrics': 60,      # 1 minute
            'aggregations': 300, # 5 minutes
            'insights': 1800,    # 30 minutes
            'alerts': 86400      # 24 hours
        }
    
    async def get_cached_data(self, cache_type, key):
        """Get cached data"""
        cache_key = f"cache:{cache_type}:{key}"
        cached_data = await self.redis_client.get(cache_key)
        
        if cached_data:
            return json.loads(cached_data)
        
        return None
    
    async def set_cached_data(self, cache_type, key, data):
        """Set cached data with TTL"""
        cache_key = f"cache:{cache_type}:{key}"
        ttl = self.cache_ttl.get(cache_type, 300)
        
        await self.redis_client.setex(
            cache_key,
            ttl,
            json.dumps(data)
        )
    
    async def invalidate_cache(self, cache_type, pattern=None):
        """Invalidate cache entries"""
        if pattern:
            # Invalidate specific pattern
            pattern_key = f"cache:{cache_type}:{pattern}*"
            keys = await self.redis_client.keys(pattern_key)
            if keys:
                await self.redis_client.delete(*keys)
        else:
            # Invalidate all entries for cache type
            pattern_key = f"cache:{cache_type}:*"
            keys = await self.redis_client.keys(pattern_key)
            if keys:
                await self.redis_client.delete(*keys)
```

## 🔧 Monitoring and Observability

### **Stream Processing Metrics**
```python
class StreamMetrics:
    def __init__(self):
        self.prometheus_client = PrometheusClient()
        self.metrics_collector = MetricsCollector()
    
    async def collect_stream_metrics(self):
        """Collect stream processing metrics"""
        metrics = {}
        
        # Event processing rate
        metrics['events_processed_per_second'] = await self.get_event_processing_rate()
        
        # Queue sizes
        metrics['queue_sizes'] = await self.get_queue_sizes()
        
        # Processing latency
        metrics['processing_latency_p95'] = await self.get_processing_latency()
        
        # Error rates
        metrics['error_rate'] = await self.get_error_rate()
        
        # WebSocket connections
        metrics['active_websocket_connections'] = await self.get_websocket_connections()
        
        # Update Prometheus metrics
        await self.update_prometheus_metrics(metrics)
        
        return metrics
    
    async def get_event_processing_rate(self):
        """Get events processed per second"""
        # Calculate from recent event logs
        one_minute_ago = datetime.now(timezone.utc) - timedelta(minutes=1)
        
        async with get_db_pool().acquire() as conn:
            count = await conn.fetchval("""
                SELECT COUNT(*) FROM competitive.events 
                WHERE timestamp >= $1
            """, one_minute_ago)
        
        return count / 60  # events per second
    
    async def update_prometheus_metrics(self, metrics):
        """Update Prometheus metrics"""
        await self.prometheus_client.gauge(
            'stream_events_per_second',
            metrics['events_processed_per_second']
        )
        
        for queue_name, size in metrics['queue_sizes'].items():
            await self.prometheus_client.gauge(
                f'stream_queue_size_{queue_name}',
                size
            )
        
        await self.prometheus_client.gauge(
            'stream_processing_latency_p95',
            metrics['processing_latency_p95']
        )
        
        await self.prometheus_client.gauge(
            'stream_error_rate',
            metrics['error_rate']
        )
        
        await self.prometheus_client.gauge(
            'websocket_active_connections',
            metrics['active_websocket_connections']
        )
```

### **Health Checks**
```python
class StreamHealthChecker:
    def __init__(self):
        self.redis_client = aioredis.Redis()
        self.websocket_manager = WebSocketManager()
    
    async def check_health(self):
        """Comprehensive health check"""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': {}
        }
        
        # Check Redis connection
        try:
            await self.redis_client.ping()
            health_status['checks']['redis'] = 'healthy'
        except Exception as e:
            health_status['checks']['redis'] = f'unhealthy: {e}'
            health_status['status'] = 'degraded'
        
        # Check WebSocket connections
        try:
            active_connections = len(self.websocket_manager.connections)
            health_status['checks']['websocket'] = f'healthy ({active_connections} connections)'
        except Exception as e:
            health_status['checks']['websocket'] = f'unhealthy: {e}'
            health_status['status'] = 'degraded'
        
        # Check event processing
        try:
            processing_rate = await self.get_processing_rate()
            if processing_rate > 0:
                health_status['checks']['event_processing'] = f'healthy ({processing_rate} events/sec)'
            else:
                health_status['checks']['event_processing'] = 'unhealthy: no events processed'
                health_status['status'] = 'degraded'
        except Exception as e:
            health_status['checks']['event_processing'] = f'unhealthy: {e}'
            health_status['status'] = 'degraded'
        
        return health_status
    
    async def get_processing_rate(self):
        """Get current event processing rate"""
        # Implementation would calculate from recent metrics
        return 100  # events per second
```

## 📈 Performance Targets

### **Real-Time Processing KPIs**
- **Event Latency**: <100ms from event generation to processing
- **Throughput**: 10,000+ events/second processing capability
- **WebSocket Latency**: <50ms for real-time updates
- **Queue Processing**: <1s for queue backlog clearance
- **Alert Latency**: <5s from detection to notification

### **Reliability KPIs**
- **Uptime**: 99.99% availability for real-time services
- **Data Loss**: <0.1% event loss during peak loads
- **Recovery Time**: <30s for service recovery
- **Backpressure Handling**: Graceful degradation under load
- **Failover**: Automatic failover with <5s switchover

### **Scalability KPIs**
- **Concurrent Users**: 500+ WebSocket connections
- **Horizontal Scaling**: Linear scaling with additional instances
- **Memory Usage**: <4GB per processing instance
- **CPU Usage**: <80% average CPU utilization
- **Network Bandwidth**: <1Gbps for 10,000 events/second

This real-time processing architecture provides the foundation for Jackdaw Sentry's sub-second competitive intelligence delivery, ensuring that users receive timely, accurate, and actionable competitive insights.
