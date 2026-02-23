-- Migration 003: Competitive Assessment Schema
-- This migration adds the competitive assessment tables to the existing database

-- Create competitive schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS competitive;

-- Competitive benchmark results table
CREATE TABLE IF NOT EXISTS competitive.benchmarks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    test_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    value DECIMAL(15,6) NOT NULL,
    unit VARCHAR(50) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Competitive metrics table
CREATE TABLE IF NOT EXISTS competitive.metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    feature VARCHAR(255) NOT NULL,
    jackdaw_value DECIMAL(15,6) NOT NULL,
    competitor_values JSONB NOT NULL,
    unit VARCHAR(50) NOT NULL,
    target_parity DECIMAL(5,2) NOT NULL,
    achieved_parity DECIMAL(5,2) NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    trend VARCHAR(20) DEFAULT 'stable',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Competitive reports table
CREATE TABLE IF NOT EXISTS competitive.reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_data JSONB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    overall_parity DECIMAL(5,2) NOT NULL,
    market_position VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Performance alerts table
CREATE TABLE IF NOT EXISTS competitive.performance_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type VARCHAR(20) NOT NULL,
    feature VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    recommendation TEXT,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Competitive trends table
CREATE TABLE IF NOT EXISTS competitive.trends (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    category_trends JSONB NOT NULL,
    overall_parity DECIMAL(5,2) NOT NULL,
    market_position VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for competitive tables
CREATE INDEX IF NOT EXISTS idx_competitive_benchmarks_test_name ON competitive.benchmarks(test_name);
CREATE INDEX IF NOT EXISTS idx_competitive_benchmarks_timestamp ON competitive.benchmarks(timestamp);
CREATE INDEX IF NOT EXISTS idx_competitive_benchmarks_metric_type ON competitive.benchmarks(metric_type);
CREATE INDEX IF NOT EXISTS idx_competitive_benchmarks_success ON competitive.benchmarks(success);

CREATE INDEX IF NOT EXISTS idx_competitive_metrics_feature ON competitive.metrics(feature);
CREATE INDEX IF NOT EXISTS idx_competitive_metrics_timestamp ON competitive.metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_competitive_metrics_parity ON competitive.metrics(achieved_parity);

CREATE INDEX IF NOT EXISTS idx_competitive_reports_generated_at ON competitive.reports(generated_at);
CREATE INDEX IF NOT EXISTS idx_competitive_reports_parity ON competitive.reports(overall_parity);

CREATE INDEX IF NOT EXISTS idx_competitive_alerts_type ON competitive.performance_alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_competitive_alerts_feature ON competitive.performance_alerts(feature);
CREATE INDEX IF NOT EXISTS idx_competitive_alerts_resolved ON competitive.performance_alerts(resolved);
CREATE INDEX IF NOT EXISTS idx_competitive_alerts_timestamp ON competitive.performance_alerts(timestamp);

CREATE INDEX IF NOT EXISTS idx_competitive_trends_timestamp ON competitive.trends(timestamp);
CREATE INDEX IF NOT EXISTS idx_competitive_trends_parity ON competitive.trends(overall_parity);

-- Create functions for competitive assessment
CREATE OR REPLACE FUNCTION competitive.get_latest_summary()
RETURNS JSONB AS $$
DECLARE
    latest_report JSONB;
BEGIN
    SELECT report_data INTO latest_report
    FROM competitive.reports 
    ORDER BY generated_at DESC 
    LIMIT 1;
    
    RETURN COALESCE(latest_report, '{}'::jsonb);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION competitive.get_active_alerts()
RETURNS JSONB AS $$
DECLARE
    alerts JSONB;
BEGIN
    SELECT jsonb_agg(
        jsonb_build_object(
            'id', id,
            'alert_type', alert_type,
            'feature', feature,
            'message', message,
            'recommendation', recommendation,
            'timestamp', timestamp
        ) ORDER BY timestamp DESC
    ) INTO alerts
    
    RETURN COALESCE(alerts, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION competitive.get_performance_trends(days INTEGER DEFAULT 30)
RETURNS JSONB AS $$
DECLARE
    trends JSONB;
BEGIN
    -- Validate input
    IF days IS NULL OR days <= 0 THEN
        RAISE EXCEPTION 'invalid "days" parameter: must be a positive integer, got %', days;
    END IF;
    
    SELECT jsonb_agg(
        jsonb_build_object(
            'timestamp', timestamp,
            'overall_parity', overall_parity,
            'market_position', market_position,
            'category_trends', category_trends
        )
    ) INTO trends
    FROM competitive.trends 
    WHERE timestamp >= NOW() - INTERVAL '1 day' * days
    ORDER BY timestamp;
    
    RETURN COALESCE(trends, '[]'::jsonb);
END;
$$ LANGUAGE plpgsql;

-- Create view for competitive dashboard summary
CREATE OR REPLACE VIEW competitive.dashboard_summary AS
SELECT 
    cr.generated_at,
    cr.overall_parity,
    cr.market_position,
    cr.report_data->'executive_summary' as executive_summary,
    (SELECT COUNT(*) FROM competitive.performance_alerts WHERE resolved = FALSE) as active_alerts_count,
    (SELECT COUNT(*) FROM competitive.benchmarks WHERE timestamp >= NOW() - INTERVAL '24 hours') as benchmarks_today
FROM competitive.reports cr
ORDER BY cr.generated_at DESC
LIMIT 1;

-- Grant permissions to the competitive schema
GRANT USAGE ON SCHEMA competitive TO jackdaw_user;
GRANT SELECT, INSERT, UPDATE ON competitive.benchmarks TO jackdaw_user;
GRANT SELECT, INSERT, UPDATE ON competitive.metrics TO jackdaw_user;
GRANT SELECT, INSERT, UPDATE ON competitive.reports TO jackdaw_user;
GRANT SELECT, INSERT, UPDATE ON competitive.performance_alerts TO jackdaw_user;
GRANT SELECT, INSERT, UPDATE ON competitive.trends TO jackdaw_user;
GRANT EXECUTE ON FUNCTION competitive.get_latest_summary() TO jackdaw_user;
GRANT EXECUTE ON FUNCTION competitive.get_active_alerts() TO jackdaw_user;
GRANT EXECUTE ON FUNCTION competitive.get_performance_trends(INTEGER) TO jackdaw_user;
GRANT SELECT ON competitive.dashboard_summary TO jackdaw_user;

-- Add comment to document the migration
COMMENT ON SCHEMA competitive IS 'Competitive assessment and benchmarking data for Jackdaw Sentry';
