#!/usr/bin/env python3
"""
Jackdaw Sentry - Security & Compliance Test Runner

Comprehensive security testing for Phase 4 modules.
Tests authentication, authorization, data privacy, input validation, and compliance.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import time
import json
from datetime import datetime, timezone

# Add project root to Python path
sys.path.append('/home/dribble0335/dev/jackdawsentry')


class SecurityTestRunner:
    """Security and compliance test runner for Phase 4"""
    
    def __init__(self):
        self.project_root = Path('/home/dribble0335/dev/jackdawsentry')
        self.test_dir = self.project_root / 'tests' / 'test_security'
        self.results_dir = self.project_root / 'tests' / 'security_results'
        self.results_dir.mkdir(exist_ok=True)
        
        self.test_modules = [
            'test_authentication.py',
            'test_data_privacy.py', 
            'test_input_validation.py'
        ]
        
        self.results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_tests': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'test_results': {}
        }
    
    def run_all_tests(self, verbose=False):
        """Run all security tests"""
        print("🔒 Starting Jackdaw Sentry Security & Compliance Tests")
        print("=" * 60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Test Directory: {self.test_dir}")
        print(f"Results Directory: {self.results_dir}")
        print("=" * 60)
        
        for test_module in self.test_modules:
            print(f"\n📋 Running {test_module}...")
            self.run_test_module(test_module, verbose)
        
        self.generate_report()
        self.print_summary()
        
        return self.results['failed'] == 0
    
    def run_test_module(self, module_name, verbose=False):
        """Run a specific test module"""
        test_file = self.test_dir / module_name
        
        if not test_file.exists():
            error_msg = f"Test file not found: {test_file}"
            self.results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return False
        
        try:
            # Run pytest with security-focused configuration
            cmd = [
                'python3', '-m', 'pytest',
                str(test_file),
                '-v' if verbose else '-q',
                '--tb=short',
                '--json-report',
                f'--json-report-file={self.results_dir}/{module_name.replace(".py", ".json")}',
                '--html-report',
                f'--html-report={self.results_dir}/{module_name.replace(".py", ".html")}',
                '--cov=src/api',
                '--cov=src/intelligence',
                '--cov=src/forensics',
                '--cov-report=html',
                f'--cov-report={self.results_dir}/{module_name.replace(".py", "_coverage")}',
                '--cov-fail-under=80'
            ]
            
            start_time = time.time()
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Parse results
            module_results = self.parse_pytest_output(result.stdout, result.stderr, result.returncode)
            module_results['duration'] = duration
            module_results['module'] = module_name
            
            self.results['test_results'][module_name] = module_results
            
            # Update totals
            self.results['total_tests'] += module_results['total']
            self.results['passed'] += module_results['passed']
            self.results['failed'] += module_results['failed']
            self.results['skipped'] += module_results['skipped']
            
            if result.returncode != 0:
                self.results['errors'].append(f"Test module {module_name} failed")
                print(f"❌ {module_name} - FAILED")
                if verbose:
                    print("STDOUT:", result.stdout)
                    print("STDERR:", result.stderr)
            else:
                print(f"✅ {module_name} - PASSED")
            
            print(f"   Duration: {duration:.2f}s")
            print(f"   Tests: {module_results['total']}, Passed: {module_results['passed']}, Failed: {module_results['failed']}")
            
        except subprocess.TimeoutExpired:
            error_msg = f"Test module {module_name} timed out"
            self.results['errors'].append(error_msg)
            print(f"⏰ {error_msg}")
        except Exception as e:
            error_msg = f"Error running {module_name}: {str(e)}"
            self.results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
    
    def parse_pytest_output(self, stdout, stderr, returncode):
        """Parse pytest output to extract test results"""
        results = {
            'total': 0,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        # Parse stdout for test results
        lines = stdout.split('\n')
        for line in lines:
            if ' passed in ' in line:
                results['passed'] += 1
            elif ' failed in ' in line:
                results['failed'] += 1
            elif ' skipped in ' in line:
                results['skipped'] += 1
            elif 'ERROR' in line:
                results['errors'].append(line.strip())
        
        # Parse stderr for additional info
        error_lines = stderr.split('\n')
        for line in error_lines:
            if 'ERROR' in line and line.strip():
                results['errors'].append(line.strip())
        
        # Calculate total
        results['total'] = results['passed'] + results['failed'] + results['skipped']
        
        return results
    
    def run_compliance_scan(self):
        """Run compliance scanning"""
        print("\n🔍 Running Compliance Scan...")
        
        compliance_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': {},
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0
        }
        
        # Check for security configuration
        security_checks = [
            ('Authentication System', self.check_authentication),
            ('Authorization System', self.check_authorization),
            ('Data Encryption', self.check_encryption),
            ('Input Validation', self.check_input_validation),
            ('Audit Logging', self.check_audit_logging),
            ('Security Headers', self.check_security_headers),
            ('Rate Limiting', self.check_rate_limiting),
            ('GDPR Compliance', self.check_gdpr_compliance)
        ]
        
        for check_name, check_func in security_checks:
            print(f"   Checking {check_name}...")
            try:
                check_result = check_func()
                compliance_results['checks'][check_name] = check_result
                compliance_results['total_checks'] += 1
                
                if check_result['passed']:
                    compliance_results['passed_checks'] += 1
                    print(f"   ✅ {check_name} - PASSED")
                else:
                    compliance_results['failed_checks'] += 1
                    print(f"   ❌ {check_name} - FAILED")
                    print(f"      Issues: {', '.join(check_result['issues'])}")
            except Exception as e:
                compliance_results['checks'][check_name] = {
                    'passed': False,
                    'issues': [f"Check failed: {str(e)}"]
                }
                compliance_results['total_checks'] += 1
                compliance_results['failed_checks'] += 1
                print(f"   ❌ {check_name} - ERROR: {str(e)}")
        
        # Save compliance results
        compliance_file = self.results_dir / 'compliance_scan.json'
        with open(compliance_file, 'w') as f:
            json.dump(compliance_results, f, indent=2)
        
        print(f"\n📊 Compliance Scan Results:")
        print(f"   Total Checks: {compliance_results['total_checks']}")
        print(f"   Passed: {compliance_results['passed_checks']}")
        print(f"   Failed: {compliance_results['failed_checks']}")
        
        return compliance_results['failed_checks'] == 0
    
    def check_authentication(self):
        """Check authentication system"""
        issues = []
        
        # Check if auth module exists
        auth_file = self.project_root / 'src' / 'api' / 'auth.py'
        if not auth_file.exists():
            issues.append("Authentication module not found")
        
        # Check JWT implementation
        try:
            with open(auth_file, 'r') as f:
                auth_content = f.read()
                if 'create_access_token' not in auth_content:
                    issues.append("JWT token creation not implemented")
                if 'verify_token' not in auth_content:
                    issues.append("JWT token verification not implemented")
        except Exception:
            issues.append("Cannot read authentication module")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_authorization(self):
        """Check authorization system"""
        issues = []
        
        # Check for permission system
        auth_file = self.project_root / 'src' / 'api' / 'auth.py'
        try:
            with open(auth_file, 'r') as f:
                auth_content = f.read()
                if 'check_permissions' not in auth_content:
                    issues.append("Permission checking not implemented")
                if 'PERMISSIONS' not in auth_content:
                    issues.append("Permission constants not defined")
        except Exception:
            issues.append("Cannot read authorization module")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_encryption(self):
        """Check encryption implementation"""
        issues = []
        
        # Check for encryption utilities
        encryption_files = [
            self.project_root / 'src' / 'utils' / 'encryption.py',
            self.project_root / 'src' / 'database' / 'gdpr_compliance.py'
        ]
        
        encryption_found = any(f.exists() for f in encryption_files)
        if not encryption_found:
            issues.append("Encryption utilities not found")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_input_validation(self):
        """Check input validation"""
        issues = []
        
        # Check for Pydantic models
        api_dir = self.project_root / 'src' / 'api' / 'routers'
        pydantic_found = False
        
        for router_file in api_dir.glob('*.py'):
            try:
                with open(router_file, 'r') as f:
                    content = f.read()
                    if 'BaseModel' in content or 'field_validator' in content:
                        pydantic_found = True
                        break
            except Exception:
                continue
        
        if not pydantic_found:
            issues.append("Pydantic validation models not found")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_audit_logging(self):
        """Check audit logging"""
        issues = []
        
        # Check for audit logging implementation
        audit_files = [
            self.project_root / 'src' / 'monitoring' / 'audit.py',
            self.project_root / 'src' / 'api' / 'middleware.py'
        ]
        
        audit_found = any(f.exists() for f in audit_files)
        if not audit_found:
            issues.append("Audit logging not implemented")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_security_headers(self):
        """Check security headers configuration"""
        issues = []
        
        # Check Nginx configuration
        nginx_config = self.project_root / 'docker' / 'nginx.conf'
        if nginx_config.exists():
            try:
                with open(nginx_config, 'r') as f:
                    config_content = f.read()
                    security_headers = [
                        'x-content-type-options',
                        'x-frame-options',
                        'x-xss-protection'
                    ]
                    
                    for header in security_headers:
                        if header not in config_content.lower():
                            issues.append(f"Security header {header} not configured")
            except Exception:
                issues.append("Cannot read Nginx configuration")
        else:
            issues.append("Nginx configuration not found")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_rate_limiting(self):
        """Check rate limiting"""
        issues = []
        
        # Check for rate limiting implementation
        rate_limit_files = [
            self.project_root / 'src' / 'rate_limiting',
            self.project_root / 'src' / 'api' / 'middleware.py'
        ]
        
        rate_limit_found = any(f.exists() for f in rate_limit_files)
        if not rate_limit_found:
            issues.append("Rate limiting not implemented")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_gdpr_compliance(self):
        """Check GDPR compliance"""
        issues = []
        
        # Check GDPR compliance features
        gdpr_files = [
            self.project_root / 'src' / 'database' / 'gdpr_compliance.py',
            self.project_root / 'docs' / 'gdpr.md'
        ]
        
        gdpr_found = any(f.exists() for f in gdpr_files)
        if not gdpr_found:
            issues.append("GDPR compliance features not found")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def generate_report(self):
        """Generate comprehensive security test report"""
        report = {
            'summary': {
                'timestamp': self.results['timestamp'],
                'total_tests': self.results['total_tests'],
                'passed': self.results['passed'],
                'failed': self.results['failed'],
                'skipped': self.results['skipped'],
                'success_rate': (self.results['passed'] / max(self.results['total_tests'], 1)) * 100
            },
            'test_results': self.results['test_results'],
            'errors': self.results['errors']
        }
        
        # Save JSON report
        report_file = self.results_dir / 'security_test_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Security test report saved to: {report_file}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🔒 SECURITY & COMPLIANCE TEST SUMMARY")
        print("=" * 60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Total Tests: {self.results['total_tests']}")
        print(f"Passed: {self.results['passed']}")
        print(f"Failed: {self.results['failed']}")
        print(f"Skipped: {self.results['skipped']}")
        print(f"Success Rate: {(self.results['passed'] / max(self.results['total_tests'], 1)) * 100:.1f}%")
        
        if self.results['errors']:
            print(f"\n⚠️  Errors ({len(self.results['errors'])}):")
            for error in self.results['errors']:
                print(f"   - {error}")
        
        if self.results['failed'] > 0:
            print(f"\n❌ {self.results['failed']} test(s) failed")
            return False
        else:
            print(f"\n✅ All security tests passed!")
            return True


def main():
    parser = argparse.ArgumentParser(description='Run Jackdaw Sentry security tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--compliance-only', action='store_true', help='Run compliance scan only')
    parser.add_argument('--module', '-m', help='Run specific test module')
    
    args = parser.parse_args()
    
    runner = SecurityTestRunner()
    
    if args.compliance_only:
        success = runner.run_compliance_scan()
    elif args.module:
        runner.run_test_module(args.module, args.verbose)
        success = runner.results['failed'] == 0
    else:
        success = runner.run_all_tests(args.verbose)
        # Also run compliance scan
        compliance_success = runner.run_compliance_scan()
        success = success and compliance_success
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
