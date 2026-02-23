# Advanced Features API Documentation

## Overview

The Advanced Features API provides endpoints for accessing Jackdaw Sentry's AI/ML capabilities, including deep learning predictions, real-time competitive intelligence, natural language processing, and advanced visualization features.

## 🧠 Machine Learning Endpoints

### **POST /api/v2/ml/predict**
Make predictions using advanced ML models.

**Request Body:**
```json
{
  "model_name": "sequential_lstm",
  "input_data": [[0.1, 0.2, 0.3, ...]],
  "version": "latest"
}
```

**Response:**
```json
{
  "prediction_id": "uuid",
  "model_name": "sequential_lstm",
  "prediction": [0.85],
  "confidence": 0.92,
  "processing_time_ms": 45,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Available Models:**
- `sequential_lstm` - Sequential pattern analysis
- `graph_cnn` - Graph structure analysis
- `cross_chain_transformer` - Cross-chain relationship analysis
- `anomaly_autoencoder` - Anomaly detection
- `isolation_forest` - Statistical anomaly detection

### **POST /api/v2/ml/batch-predict**
Make batch predictions for multiple inputs.

**Request Body:**
```json
{
  "model_name": "sequential_lstm",
  "input_data": [
    [0.1, 0.2, 0.3, ...],
    [0.4, 0.5, 0.6, ...]
  ],
  "version": "latest"
}
```

**Response:**
```json
{
  "batch_id": "uuid",
  "predictions": [
    {
      "prediction": [0.85],
      "confidence": 0.92
    },
    {
      "prediction": [0.23],
      "confidence": 0.78
    }
  ],
  "total_processing_time_ms": 89,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### **GET /api/v2/ml/models**
List available ML models.

**Response:**
```json
{
  "models": [
    {
      "name": "sequential_lstm",
      "type": "lstm",
      "description": "Sequential pattern detection",
      "versions": ["1.0.0", "1.1.0"],
      "latest_version": "1.1.0",
      "performance": {
        "accuracy": 0.95,
        "inference_time_ms": 45
      }
    }
  ]
}
```

### **GET /api/v2/ml/models/{model_name}/info**
Get detailed information about a specific model.

**Response:**
```json
{
  "name": "sequential_lstm",
  "type": "lstm",
  "description": "Sequential pattern detection",
  "version": "1.1.0",
  "architecture": {
    "input_size": 128,
    "hidden_size": 256,
    "num_layers": 3,
    "bidirectional": true
  },
  "performance_metrics": {
    "accuracy": 0.95,
    "precision": 0.93,
    "recall": 0.94,
    "f1_score": 0.935,
    "inference_time_ms": 45
  },
  "training_data": {
    "dataset_size": 100000,
    "training_date": "2024-01-01",
    "validation_split": 0.2
  }
}
```

## ⚡ Real-Time Processing Endpoints

### **POST /api/v2/realtime/events**
Publish real-time events for processing.

**Request Body:**
```json
{
  "event_type": "benchmark_completed",
  "data": {
    "benchmark_id": "uuid",
    "results": {
      "score": 0.92,
      "competitor": "Chainalysis"
    }
  },
  "priority": "normal"
}
```

**Response:**
```json
{
  "event_id": "uuid",
  "status": "published",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### **GET /api/v2/realtime/events**
Get recent real-time events.

**Query Parameters:**
- `event_type` - Filter by event type
- `limit` - Number of events to return (default: 100)
- `since` - Get events since timestamp

**Response:**
```json
{
  "events": [
    {
      "event_id": "uuid",
      "event_type": "benchmark_completed",
      "data": {...},
      "processed": true,
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "total_count": 150,
  "has_more": true
}
```

### **GET /api/v2/realtime/metrics**
Get real-time processing metrics.

**Response:**
```json
{
  "metrics": {
    "events_processed_per_second": 125.5,
    "queue_size": 23,
    "processing_latency_p95_ms": 89,
    "error_rate": 0.02,
    "active_websocket_connections": 45
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### **WebSocket /api/v2/realtime/ws**
WebSocket endpoint for real-time updates.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v2/realtime/ws');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
};
```

**Message Format:**
```json
{
  "type": "dashboard_update",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "competitive_parity": 0.92,
    "anomaly_count": 3,
    "performance_metrics": {...}
  }
}
```

## 🤖 Natural Language Processing Endpoints

### **POST /api/v2/nlp/analyze**
Analyze text using NLP models.

**Request Body:**
```json
{
  "text": "Jackdaw Sentry shows superior performance in blockchain analysis",
  "analysis_type": "sentiment",
  "context": "competitive_analysis"
}
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "text": "Jackdaw Sentry shows superior performance in blockchain analysis",
  "analysis_type": "sentiment",
  "results": {
    "sentiment": "positive",
    "confidence": 0.87,
    "entities": [
      {
        "text": "Jackdaw Sentry",
        "type": "PRODUCT",
        "confidence": 0.95
      }
    ],
    "keywords": ["performance", "blockchain", "analysis"]
  },
  "processing_time_ms": 123
}
```

### **POST /api/v2/nlp/generate-insight**
Generate AI-powered competitive insights.

**Request Body:**
```json
{
  "data_context": {
    "competitive_parity": 0.92,
    "recent_benchmarks": [...],
    "market_trends": [...]
  },
  "insight_type": "executive_summary",
  "format": "markdown"
}
```

**Response:**
```json
{
  "insight_id": "uuid",
  "insight_type": "executive_summary",
  "content": "# Competitive Analysis Summary\n\nJackdaw Sentry demonstrates...",
  "confidence": 0.91,
  "key_points": [
    "92% competitive parity achieved",
    "Strong performance in pattern detection"
  ],
  "recommendations": [
    "Focus on scaling capabilities",
    "Enhance real-time processing"
  ],
  "generated_at": "2024-01-01T12:00:00Z"
}
```

### **POST /api/v2/nlp/summarize**
Generate summaries of competitive data.

**Request Body:**
```json
{
  "content": "Long competitive analysis text...",
  "summary_type": "executive",
  "max_length": 200,
  "format": "bullet_points"
}
```

**Response:**
```json
{
  "summary_id": "uuid",
  "summary": "• Jackdaw Sentry achieves 92% competitive parity\n• Superior pattern detection capabilities\n• Real-time processing under 100ms",
  "compression_ratio": 0.15,
  "key_topics": ["competitive_parity", "pattern_detection", "real_time"],
  "generated_at": "2024-01-01T12:00:00Z"
}
```

## 🎨 Visualization Endpoints

### **POST /api/v2/visualization/create**
Create advanced visualizations.

**Request Body:**
```json
{
  "visualization_type": "3d_network",
  "data": {
    "nodes": [...],
    "edges": [...],
    "layout": "force_directed"
  },
  "config": {
    "interactive": true,
    "animation": true,
    "theme": "dark"
  }
}
```

**Response:**
```json
{
  "visualization_id": "uuid",
  "type": "3d_network",
  "render_url": "/api/v2/visualization/render/uuid",
  "config": {
    "interactive": true,
    "animation": true,
    "theme": "dark"
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

### **GET /api/v2/visualization/render/{visualization_id}**
Render visualization as interactive chart.

**Response:**
```json
{
  "visualization_id": "uuid",
  "chart_data": {
    "data": [...],
    "layout": {...}
  },
  "render_time_ms": 234,
  "interactive_features": ["zoom", "pan", "filter", "export"]
}
```

### **POST /api/v2/visualization/dashboard**
Create comprehensive dashboard.

**Request Body:**
```json
{
  "dashboard_name": "Competitive Intelligence Dashboard",
  "components": [
    {
      "type": "parity_chart",
      "position": {"x": 0, "y": 0, "w": 6, "h": 4},
      "config": {...}
    },
    {
      "type": "performance_trends",
      "position": {"x": 6, "y": 0, "w": 6, "h": 4},
      "config": {...}
    }
  ]
}
```

**Response:**
```json
{
  "dashboard_id": "uuid",
  "name": "Competitive Intelligence Dashboard",
  "components": [
    {
      "component_id": "uuid",
      "type": "parity_chart",
      "render_url": "/api/v2/visualization/component/uuid"
    }
  ],
  "created_at": "2024-01-01T12:00:00Z"
}
```

## 👁 Computer Vision Endpoints

### **POST /api/v2/cv/analyze-image**
Analyze images for competitive intelligence.

**Request Body (multipart/form-data):**
```
image: [file]
analysis_type: logo_detection
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "image_info": {
    "width": 1920,
    "height": 1080,
    "format": "jpeg",
    "size_bytes": 245760
  },
  "results": {
    "logos_detected": [
      {
        "logo": "Chainalysis",
        "confidence": 0.94,
        "bounding_box": {"x": 100, "y": 50, "width": 200, "height": 80}
      }
    ],
    "brand_colors": ["#1f77b4", "#ff7f0e"],
    "text_content": ["Blockchain Analysis Platform"]
  },
  "processing_time_ms": 456
}
```

### **POST /api/v2/cv/analyze-chart**
Extract data from charts and graphs.

**Request Body (multipart/form-data):**
```
image: [file]
chart_type: bar_chart
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "chart_type": "bar_chart",
  "extracted_data": {
    "categories": ["Jackdaw", "CompetitorA", "CompetitorB"],
    "values": [92, 85, 78],
    "confidence": 0.89
  },
  "structured_data": {
    "json": {"categories": [...], "values": [...]},
    "csv": "category,value\nJackdaw,92\n..."
  },
  "processing_time_ms": 678
}
```

## 🎯 Reinforcement Learning Endpoints

### **POST /api/v2/rl/optimize`
Optimize system parameters using reinforcement learning.

**Request Body:**
```json
{
  "optimization_target": "anomaly_detection_threshold",
  "current_parameters": {
    "threshold": 0.05,
    "min_confidence": 0.8
  },
  "performance_metrics": {
    "false_positive_rate": 0.02,
    "detection_rate": 0.95
  },
  "optimization_goal": "minimize_false_positives"
}
```

**Response:**
```json
{
  "optimization_id": "uuid",
  "target": "anomaly_detection_threshold",
  "optimized_parameters": {
    "threshold": 0.047,
    "min_confidence": 0.82
  },
  "expected_improvement": {
    "false_positive_rate_reduction": 0.15,
    "detection_rate_change": -0.02
  },
  "confidence": 0.87,
  "optimization_iterations": 150
}
```

### **GET /api/v2/rl/policies`
Get available reinforcement learning policies.

**Response:**
```json
{
  "policies": [
    {
      "name": "threshold_optimization",
      "description": "Optimize detection thresholds",
      "state_space": "threshold_values",
      "action_space": "threshold_adjustments",
      "reward_function": "detection_accuracy",
      "performance": {
        "average_reward": 0.78,
        "convergence_episodes": 120
      }
    }
  ]
}
```

## 📊 Advanced Analytics Endpoints

### **POST /api/v2/analytics/predictive-analysis**
Generate predictive competitive analysis.

**Request Body:**
```json
{
  "analysis_type": "market_forecast",
  "time_horizon": "30d",
  "data_sources": ["benchmarks", "market_trends", "competitor_activity"],
  "confidence_level": 0.95
}
```

**Response:**
```json
{
  "analysis_id": "uuid",
  "forecast": {
    "competitive_parity_trend": "increasing",
    "predicted_parity_30d": 0.94,
    "confidence_interval": [0.91, 0.97],
    "key_factors": [
      "Improved pattern detection",
      "Enhanced real-time processing"
    ]
  },
  "risk_assessment": {
    "market_risk": "low",
    "competitive_risk": "medium",
    "technical_risk": "low"
  },
  "recommendations": [
    "Focus on scaling infrastructure",
    "Enhance customer onboarding"
  ]
}
```

### **POST /api/v2/analytics/what-if-analysis**
Perform what-if scenario analysis.

**Request Body:**
```json
{
  "scenario": "competitor_price_reduction",
  "parameters": {
    "price_reduction_percentage": 20,
    "timeframe": "90d"
  },
  "baseline_metrics": {
    "market_share": 0.15,
    "revenue": 1000000
  }
}
```

**Response:**
```json
{
  "scenario_id": "uuid",
  "scenario": "competitor_price_reduction",
  "impact_analysis": {
    "market_share_change": -0.03,
    "revenue_impact": -150000,
    "confidence": 0.78
  },
  "mitigation_strategies": [
    "Enhance value proposition",
    "Improve customer retention"
  ],
  "break_even_point": "45d"
}
```

## 🔧 System Management Endpoints

### **GET /api/v2/system/health**
Get comprehensive system health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "components": {
    "ml_engine": {
      "status": "healthy",
      "models_loaded": 5,
      "average_inference_time_ms": 45
    },
    "real_time_processor": {
      "status": "healthy",
      "events_per_second": 125.5,
      "queue_size": 23
    },
    "nlp_engine": {
      "status": "healthy",
      "models_loaded": 3,
      "average_processing_time_ms": 123
    },
    "database": {
      "status": "healthy",
      "connection_pool": "80% utilized",
      "query_latency_p95_ms": 12
    }
  }
}
```

### **GET /api/v2/system/performance**
Get system performance metrics.

**Response:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "performance": {
    "cpu_utilization": 0.65,
    "memory_utilization": 0.78,
    "gpu_utilization": 0.45,
    "disk_io": "125 MB/s",
    "network_io": "45 MB/s"
  },
  "ml_performance": {
    "total_predictions_per_second": 1250,
    "average_inference_time_ms": 45,
    "model_accuracy": 0.94
  },
  "real_time_performance": {
    "events_processed_per_second": 125.5,
    "processing_latency_p95_ms": 89,
    "websocket_connections": 45
  }
}
```

### **POST /api/v2/system/optimize-trigger`
Trigger system optimization.

**Request Body:**
```json
{
  "optimization_type": "model_retraining",
  "target_models": ["sequential_lstm", "graph_cnn"],
  "priority": "high"
}
```

**Response:**
```json
{
  "optimization_id": "uuid",
  "type": "model_retraining",
  "status": "initiated",
  "estimated_completion_time": "2024-01-01T14:00:00Z",
  "target_models": ["sequential_lstm", "graph_cnn"]
}
```

## 🔐 Authentication & Authorization

All advanced features endpoints require JWT authentication with appropriate permissions:

- `ml:read` - Access to ML prediction endpoints
- `ml:write` - Access to model management endpoints
- `realtime:read` - Access to real-time event endpoints
- `nlp:read` - Access to NLP analysis endpoints
- `visualization:read` - Access to visualization endpoints
- `cv:read` - Access to computer vision endpoints
- `rl:write` - Access to reinforcement learning endpoints
- `analytics:read` - Access to advanced analytics endpoints

**Example Request Headers:**
```
Authorization: Bearer <jwt_token>
Content-Type: application/json
```

## 📈 Rate Limiting

Advanced features endpoints have the following rate limits:

- ML Prediction: 1000 requests/minute
- Real-time Events: 10000 events/minute
- NLP Analysis: 500 requests/minute
- Visualization: 200 requests/minute
- Computer Vision: 100 requests/minute
- Analytics: 300 requests/minute

## 🚀 Quick Start Examples

### **Python Example**
```python
import requests
import json

# Authentication
headers = {
    'Authorization': 'Bearer <jwt_token>',
    'Content-Type': 'application/json'
}

# Make ML prediction
prediction_data = {
    'model_name': 'sequential_lstm',
    'input_data': [[0.1, 0.2, 0.3] * 43]
}

response = requests.post(
    'http://localhost:8000/api/v2/ml/predict',
    headers=headers,
    json=prediction_data
)

result = response.json()
print(f"Prediction: {result['prediction']}, Confidence: {result['confidence']}")
```

### **JavaScript Example**
```javascript
// Real-time WebSocket connection
const ws = new WebSocket('ws://localhost:8000/api/v2/realtime/ws');

ws.onopen = function() {
  console.log('Connected to real-time updates');
};

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Real-time update:', data);
  
  if (data.type === 'dashboard_update') {
    updateDashboard(data.data);
  }
};

// Generate AI insight
fetch('/api/v2/nlp/generate-insight', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <jwt_token>',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    data_context: {
      competitive_parity: 0.92,
      recent_benchmarks: [...]
    },
    insight_type: 'executive_summary'
  })
})
.then(response => response.json())
.then(data => {
  console.log('Generated insight:', data.content);
});
```

This API documentation provides comprehensive coverage of Jackdaw Sentry's advanced features endpoints, enabling developers to integrate cutting-edge AI/ML capabilities into their applications.
