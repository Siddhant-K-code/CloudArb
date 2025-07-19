-- CloudArb Database Initialization Script
-- This script sets up the initial database schema and extensions

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create custom types
CREATE TYPE workload_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE optimization_status AS ENUM ('pending', 'running', 'completed', 'failed', 'cancelled');
CREATE TYPE workload_type AS ENUM ('training', 'inference', 'fine-tuning', 'data-processing');
CREATE TYPE optimization_type AS ENUM ('cost', 'performance', 'balanced', 'risk-adjusted');

-- Create organizations table
CREATE TABLE organizations (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create roles table
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    permissions JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create users table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    organization_id INTEGER REFERENCES organizations(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create user_roles junction table
CREATE TABLE user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Create API keys table
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    permissions JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT true,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create providers table
CREATE TABLE providers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT true,
    config JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create instance_types table
CREATE TABLE instance_types (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    provider_id INTEGER REFERENCES providers(id) ON DELETE CASCADE,
    gpu_count INTEGER DEFAULT 0,
    gpu_memory_gb INTEGER DEFAULT 0,
    cpu_count INTEGER DEFAULT 0,
    memory_gb INTEGER DEFAULT 0,
    storage_gb INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    specs JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider_id, name)
);

-- Create pricing_data table (TimescaleDB hypertable)
CREATE TABLE pricing_data (
    id SERIAL,
    provider_id INTEGER REFERENCES providers(id) ON DELETE CASCADE,
    instance_type_id INTEGER REFERENCES instance_types(id) ON DELETE CASCADE,
    region VARCHAR(100) NOT NULL,
    price_per_hour DECIMAL(10,4) NOT NULL,
    spot_price DECIMAL(10,4),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Convert pricing_data to TimescaleDB hypertable
SELECT create_hypertable('pricing_data', 'timestamp', chunk_time_interval => INTERVAL '1 day');

-- Create workloads table
CREATE TABLE workloads (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    workload_type workload_type NOT NULL,
    gpu_count INTEGER NOT NULL,
    gpu_memory_gb INTEGER NOT NULL,
    cpu_count INTEGER NOT NULL,
    memory_gb INTEGER NOT NULL,
    storage_gb INTEGER NOT NULL,
    estimated_duration_hours DECIMAL(8,2) NOT NULL,
    priority INTEGER DEFAULT 1,
    budget_per_hour DECIMAL(10,4) NOT NULL,
    deadline TIMESTAMP WITH TIME ZONE,
    requirements JSONB DEFAULT '{}',
    status workload_status DEFAULT 'pending',
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create optimization_runs table
CREATE TABLE optimization_runs (
    id SERIAL PRIMARY KEY,
    optimization_type optimization_type NOT NULL,
    status optimization_status DEFAULT 'pending',
    total_cost DECIMAL(12,4) DEFAULT 0,
    total_savings DECIMAL(12,4) DEFAULT 0,
    constraints JSONB DEFAULT '{}',
    results JSONB DEFAULT '{}',
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create workload_optimization_runs junction table
CREATE TABLE workload_optimization_runs (
    workload_id INTEGER REFERENCES workloads(id) ON DELETE CASCADE,
    optimization_run_id INTEGER REFERENCES optimization_runs(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (workload_id, optimization_run_id)
);

-- Create allocations table
CREATE TABLE allocations (
    id SERIAL PRIMARY KEY,
    workload_id INTEGER REFERENCES workloads(id) ON DELETE CASCADE,
    optimization_run_id INTEGER REFERENCES optimization_runs(id) ON DELETE CASCADE,
    provider VARCHAR(100) NOT NULL,
    instance_type VARCHAR(255) NOT NULL,
    region VARCHAR(100) NOT NULL,
    gpu_count INTEGER NOT NULL,
    duration_hours DECIMAL(8,2) NOT NULL,
    cost_per_hour DECIMAL(10,4) NOT NULL,
    total_cost DECIMAL(12,4) NOT NULL,
    status VARCHAR(50) DEFAULT 'allocated',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create arbitrage_opportunities table
CREATE TABLE arbitrage_opportunities (
    id SERIAL PRIMARY KEY,
    provider_from VARCHAR(100) NOT NULL,
    provider_to VARCHAR(100) NOT NULL,
    instance_type VARCHAR(255) NOT NULL,
    region VARCHAR(100) NOT NULL,
    cost_savings_percent DECIMAL(5,2) NOT NULL,
    cost_savings_amount DECIMAL(10,4) NOT NULL,
    risk_score DECIMAL(3,2) DEFAULT 0,
    confidence_score DECIMAL(3,2) DEFAULT 0,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create analytics table
CREATE TABLE analytics (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(15,4) NOT NULL,
    metric_unit VARCHAR(50),
    dimensions JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);
CREATE INDEX idx_workloads_user ON workloads(user_id);
CREATE INDEX idx_workloads_status ON workloads(status);
CREATE INDEX idx_workloads_type ON workloads(workload_type);
CREATE INDEX idx_optimization_runs_user ON optimization_runs(user_id);
CREATE INDEX idx_optimization_runs_status ON optimization_runs(status);
CREATE INDEX idx_pricing_data_provider_instance ON pricing_data(provider_id, instance_type_id);
CREATE INDEX idx_pricing_data_timestamp ON pricing_data(timestamp DESC);
CREATE INDEX idx_allocations_workload ON allocations(workload_id);
CREATE INDEX idx_arbitrage_opportunities_savings ON arbitrage_opportunities(cost_savings_percent DESC);
CREATE INDEX idx_analytics_user_metric ON analytics(user_id, metric_name);
CREATE INDEX idx_analytics_timestamp ON analytics(timestamp DESC);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_roles_updated_at BEFORE UPDATE ON roles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_providers_updated_at BEFORE UPDATE ON providers FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_instance_types_updated_at BEFORE UPDATE ON instance_types FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_workloads_updated_at BEFORE UPDATE ON workloads FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_optimization_runs_updated_at BEFORE UPDATE ON optimization_runs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_allocations_updated_at BEFORE UPDATE ON allocations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default roles
INSERT INTO roles (name, description, permissions) VALUES
('admin', 'Administrator with full access', '{"*": "*"}'),
('user', 'Standard user with basic access', '{"workloads": ["read", "write"], "optimization": ["read", "write"], "analytics": ["read"]}'),
('viewer', 'Read-only user', '{"workloads": ["read"], "optimization": ["read"], "analytics": ["read"]}');

-- Insert default providers
INSERT INTO providers (name, display_name, description) VALUES
('aws', 'Amazon Web Services', 'AWS cloud computing platform'),
('gcp', 'Google Cloud Platform', 'Google Cloud computing platform'),
('azure', 'Microsoft Azure', 'Microsoft cloud computing platform'),
('lambda', 'Lambda Labs', 'Lambda Labs GPU cloud platform'),
('runpod', 'RunPod', 'RunPod GPU cloud platform');

-- Insert default organization
INSERT INTO organizations (name, slug, description) VALUES
('Default Organization', 'default', 'Default organization for new users');

-- Create default admin user (password: admin123)
INSERT INTO users (email, hashed_password, first_name, last_name, organization_id, is_verified) VALUES
('admin@cloudarb.com', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.iK8i', 'Admin', 'User', 1, true);

-- Assign admin role to default user
INSERT INTO user_roles (user_id, role_id) VALUES (1, 1);

-- Create views for common queries
CREATE VIEW workload_summary AS
SELECT
    w.id,
    w.name,
    w.workload_type,
    w.status,
    w.gpu_count,
    w.budget_per_hour,
    w.estimated_duration_hours,
    u.email as user_email,
    o.name as organization_name,
    w.created_at
FROM workloads w
JOIN users u ON w.user_id = u.id
LEFT JOIN organizations o ON w.organization_id = o.id;

CREATE VIEW optimization_summary AS
SELECT
    o.id,
    o.optimization_type,
    o.status,
    o.total_cost,
    o.total_savings,
    u.email as user_email,
    o.created_at
FROM optimization_runs o
JOIN users u ON o.user_id = u.id;

CREATE VIEW cost_analysis AS
SELECT
    p.name as provider,
    it.name as instance_type,
    pd.region,
    pd.price_per_hour,
    pd.spot_price,
    pd.timestamp
FROM pricing_data pd
JOIN providers p ON pd.provider_id = p.id
JOIN instance_types it ON pd.instance_type_id = it.id
WHERE pd.timestamp >= CURRENT_TIMESTAMP - INTERVAL '24 hours';

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cloudarb;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cloudarb;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO cloudarb;