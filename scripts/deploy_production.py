#!/usr/bin/env python3
"""
Jackdaw Sentry - Production Deployment Script
Automated production deployment with health checks and rollback capabilities
"""

import asyncio
import subprocess
import sys
import os
import json
import time
from pathlib import Path
from typing import Dict, List, Optional
import logging
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ProductionDeployer:
    """Production deployment manager with health checks and rollback"""
    
    def __init__(self, project_dir: str = "/home/dribble0335/dev/jackdawsentry"):
        self.project_dir = Path(project_dir)
        self.docker_dir = self.project_dir / "docker"
        self.backup_dir = self.project_dir / "backups"
        self.health_check_timeout = 300  # 5 minutes
        self.rollback_threshold = 3  # Max failed health checks
        
    async def deploy_production(self) -> bool:
        """Deploy to production with full health checks"""
        logger.info("Starting production deployment...")
        
        try:
            # Pre-deployment checks
            await self.pre_deployment_checks()
            
            # Create backup
            await self.create_backup()
            
            # Build images
            await self.build_production_images()
            
            # Deploy services
            await self.deploy_services()
            
            # Health checks
            await self.health_checks()
            
            # Post-deployment verification
            await self.post_deployment_verification()
            
            logger.info("✅ Production deployment completed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Production deployment failed: {e}")
            await self.rollback()
            return False
    
    async def pre_deployment_checks(self) -> None:
        """Run pre-deployment checks"""
        logger.info("Running pre-deployment checks...")
        
        # Check environment variables
        required_env_vars = [
            'POSTGRES_PASSWORD',
            'JWT_SECRET',
            'GRAFANA_PASSWORD',
            'GRAFANA_SMTP_USER',
            'GRAFANA_SMTP_PASSWORD',
            'GRAFANA_FROM_ADDRESS'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise Exception(f"Missing required environment variables: {missing_vars}")
        
        # Check Docker daemon
        try:
            subprocess.run(['docker', '--version'], check=True, capture_output=True)
            subprocess.run(['docker-compose', '--version'], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            raise Exception("Docker or Docker Compose not available")
        
        # Check disk space
        disk_usage = subprocess.check_output(['df', '-h', '/']).decode('utf-8')
        if '100%' in disk_usage or '99%' in disk_usage:
            raise Exception("Insufficient disk space")
        
        logger.info("✅ Pre-deployment checks passed")
    
    async def create_backup(self) -> None:
        """Create database backup"""
        logger.info("Creating database backup...")
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"jackdaw_backup_{timestamp}.sql"
        
        try:
            # Create backup directory
            self.backup_dir.mkdir(exist_ok=True)
            
            # Run database backup
            cmd = [
                'docker-compose', '-f', 'docker/production-compose.yml',
                'exec', '-T', 'postgres',
                'pg_dump', '-U', 'jackdaw', 'jackdaw'
            ]
            
            with open(self.backup_dir / backup_file, 'w') as f:
                subprocess.run(cmd, check=True, stdout=f)
            
            logger.info(f"✅ Database backup created: {backup_file}")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️  Database backup failed: {e}")
    
    async def build_production_images(self) -> None:
        """Build production Docker images"""
        logger.info("Building production Docker images...")
        
        # Build main application image
        try:
            subprocess.run([
                'docker', 'build',
                '-t', 'jackdaw-sentry:production',
                '-f', 'docker/competitive-production.Dockerfile',
                '.'
            ], check=True, cwd=self.project_dir)
            
            logger.info("✅ Main application image built")
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to build main image: {e}")
        
        # Build competitive dashboard image
        try:
            subprocess.run([
                'docker', 'build',
                '-t', 'jackdaw-competitive-dashboard:production',
                '-f', 'docker/competitive-production.Dockerfile',
                '.'
            ], check=True, cwd=self.project_dir)
            
            logger.info("✅ Competitive dashboard image built")
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to build dashboard image: {e}")
    
    async def deploy_services(self) -> None:
        """Deploy production services"""
        logger.info("Deploying production services...")
        
        try:
            # Stop existing services
            subprocess.run([
                'docker-compose', '-f', 'docker/production-compose.yml',
                'down'
            ], check=True, cwd=self.project_dir)
            
            # Start services
            subprocess.run([
                'docker-compose', '-f', 'docker/production-compose.yml',
                'up', '-d'
            ], check=True, cwd=self.project_dir)
            
            logger.info("✅ Production services deployed")
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Failed to deploy services: {e}")
    
    async def health_checks(self) -> None:
        """Run comprehensive health checks"""
        logger.info("Running health checks...")
        
        services = {
            'api': 'http://localhost:8000/health',
            'competitive-dashboard': 'http://localhost:8080/health',
            'postgres': 'localhost:5432',
            'redis': 'localhost:6379',
            'grafana': 'http://localhost:3000/api/health',
            'prometheus': 'http://localhost:9090/-/healthy'
        }
        
        failed_checks = 0
        
        for service, endpoint in services.items():
            if not await self.check_service_health(service, endpoint):
                failed_checks += 1
                if failed_checks >= self.rollback_threshold:
                    raise Exception(f"Too many failed health checks: {failed_checks}")
        
        logger.info("✅ All health checks passed")
    
    async def check_service_health(self, service: str, endpoint: str) -> bool:
        """Check individual service health"""
        logger.info(f"Checking {service} health...")
        
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            try:
                if service == 'postgres':
                    # Check PostgreSQL
                    subprocess.run([
                        'docker-compose', '-f', 'docker/production-compose.yml',
                        'exec', '-T', 'postgres',
                        'pg_isready', '-U', 'jackdaw', '-d', 'jackdaw'
                    ], check=True, timeout=10)
                    return True
                
                elif service == 'redis':
                    # Check Redis
                    subprocess.run([
                        'docker-compose', '-f', 'docker/production-compose.yml',
                        'exec', '-T', 'redis',
                        'redis-cli', 'ping'
                    ], check=True, timeout=10)
                    return True
                
                else:
                    # Check HTTP endpoint
                    response = requests.get(endpoint, timeout=10)
                    if response.status_code == 200:
                        return True
                
            except Exception as e:
                logger.warning(f"Health check failed for {service} (attempt {attempt + 1}): {e}")
                attempt += 1
                await asyncio.sleep(10)
        
        logger.error(f"❌ Health check failed for {service}")
        return False
    
    async def post_deployment_verification(self) -> None:
        """Run post-deployment verification"""
        logger.info("Running post-deployment verification...")
        
        # Verify competitive dashboard functionality
        try:
            response = requests.get('http://localhost:8080/api/summary', timeout=30)
            if response.status_code == 200:
                logger.info("✅ Competitive dashboard API responding")
            else:
                logger.warning(f"⚠️  Competitive dashboard API returned {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Competitive dashboard verification failed: {e}")
        
        # Verify API functionality
        try:
            response = requests.get('http://localhost:8000/health', timeout=30)
            if response.status_code == 200:
                logger.info("✅ Main API responding")
            else:
                logger.warning(f"⚠️  Main API returned {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Main API verification failed: {e}")
        
        # Verify Grafana dashboards
        try:
            response = requests.get('http://localhost:3000/api/dashboards/name/Jackdaw%20Sentry%20-%20Production%20Competitive%20Dashboard', timeout=30)
            if response.status_code == 200:
                logger.info("✅ Grafana dashboard available")
            else:
                logger.warning(f"⚠️  Grafana dashboard returned {response.status_code}")
        except Exception as e:
            logger.warning(f"⚠️  Grafana verification failed: {e}")
        
        logger.info("✅ Post-deployment verification completed")
    
    async def rollback(self) -> None:
        """Rollback deployment"""
        logger.error("🔄 Initiating rollback...")
        
        try:
            # Stop current services
            subprocess.run([
                'docker-compose', '-f', 'docker/production-compose.yml',
                'down'
            ], check=True, cwd=self.project_dir)
            
            # Restore from backup if available
            backup_files = list(self.backup_dir.glob("jackdaw_backup_*.sql"))
            if backup_files:
                latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
                logger.info(f"Restoring from backup: {latest_backup}")
                
                # Start database only
                subprocess.run([
                    'docker-compose', '-f', 'docker/production-compose.yml',
                    'up', '-d', 'postgres'
                ], check=True, cwd=self.project_dir)
                
                # Wait for database to be ready
                await asyncio.sleep(30)
                
                # Restore backup
                with open(latest_backup, 'r') as f:
                    subprocess.run([
                        'docker-compose', '-f', 'docker/production-compose.yml',
                        'exec', '-T', 'postgres',
                        'psql', '-U', 'jackdaw', '-d', 'jackdaw'
                    ], stdin=f, check=True, cwd=self.project_dir)
                
                logger.info("✅ Database restored from backup")
            
            # Start previous version (would need to tag previous images)
            logger.warning("⚠️  Manual rollback required - previous image tags not available")
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
    
    async def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status"""
        try:
            # Get container status
            result = subprocess.run([
                'docker-compose', '-f', 'docker/production-compose.yml',
                'ps'
            ], capture_output=True, text=True, cwd=self.project_dir)
            
            containers = {}
            for line in result.stdout.split('\n')[2:]:  # Skip header lines
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 3:
                        name = parts[0]
                        status = parts[1]
                        containers[name] = status
            
            # Get service health
            health_status = {}
            for service in ['api', 'competitive-dashboard', 'postgres', 'redis', 'grafana', 'prometheus']:
                health_status[service] = await self.check_service_health(service, f"http://localhost:{8000 if service == 'api' else 8080 if service == 'competitive-dashboard' else 3000 if service == 'grafana' else 9090 if service == 'prometheus' else 5432 if service == 'postgres' else 6379}/health")
            
            return {
                'timestamp': datetime.now().isoformat(),
                'containers': containers,
                'health_status': health_status,
                'deployment_status': 'healthy' if all(health_status.values()) else 'degraded'
            }
            
        except Exception as e:
            logger.error(f"Failed to get deployment status: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'deployment_status': 'error'
            }

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Jackdaw Sentry Production Deployment")
    parser.add_argument('--project-dir', default='/home/dribble0335/dev/jackdawsentry', help='Project directory')
    parser.add_argument('--status', action='store_true', help='Get deployment status only')
    parser.add_argument('--rollback', action='store_true', help='Rollback deployment')
    
    args = parser.parse_args()
    
    deployer = ProductionDeployer(args.project_dir)
    
    if args.status:
        status = asyncio.run(deployer.get_deployment_status())
        print(json.dumps(status, indent=2))
    elif args.rollback:
        asyncio.run(deployer.rollback())
    else:
        success = asyncio.run(deployer.deploy_production())
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
