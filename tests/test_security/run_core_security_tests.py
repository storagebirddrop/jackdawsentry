#!/usr/bin/env python3
"""
Jackdaw Sentry - Core Security Test Runner (Phases 1-3)

Comprehensive security testing for core modules (compliance, analysis, blockchain, authentication).
Tests authentication, authorization, data privacy, and compliance for Phases 1-3.
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


class CoreSecurityTestRunner:
    """Core security and compliance test runner for Phases 1-3"""
    
    def __init__(self):
        self.project_root = Path('/home/dribble0335/dev/jackdawsentry')
        self.test_dir = self.project_root / 'tests' / 'test_security'
        self.results_dir = self.project_root / 'tests' / 'core_security_results'
        self.results_dir.mkdir(exist_ok=True)
        
        self.core_modules = [
            'test_auth_security.py',
            'test_compliance_security.py', 
            'test_analysis_security.py',
            'test_blockchain_security.py'
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
        """Run all core security tests"""
        print("🔒 Starting Jackdaw Sentry Core Security Tests (Phases 1-3)")
        print("=" * 60)
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Test Directory: {self.test_dir}")
        print(f"Results Directory: {self.results_dir}")
        print("=" * 60)
        
        for test_module in self.core_modules:
            print(f"\n📋 Running {test_module}...")
            self.run_test_module(test_module, verbose)
        
        self.generate_report()
        self.print_summary()
        
        return self.results['failed'] == 0
    
    def run_test_module(self, module_name, verbose=False):
        """Run a specific core security test module"""
        test_file = self.test_dir / module_name
        
        if not test_file.exists():
            error_msg = f"Test file not found: {test_file}"
            self.results['errors'].append(error_msg)
            print(f"❌ {error_msg}")
            return False
        
        try:
            # Run pytest with core security focus
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
                '--cov=src/compliance',
                '--cov=src/analysis',
                '--cov=src/blockchain',
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
    
    def run_module_specific_tests(self, module, verbose=False):
        """Run tests for a specific module"""
        module_tests = {
            'compliance': ['test_compliance_security.py'],
            'analysis': ['test_analysis_security.py'],
            'blockchain': ['test_blockchain_security.py'],
            'auth': ['test_auth_security.py'],
            'all': self.core_modules
        }
        
        if module not in module_tests:
            print(f"❌ Unknown module: {module}")
            print(f"Available modules: {list(module_tests.keys())}")
            return False
        
        tests_to_run = module_tests[module]
        
        print(f"🔒 Running {module} security tests...")
        
        for test_module in tests_to_run:
            print(f"\n📋 Running {test_module}...")
            self.run_test_module(test_module, verbose)
        
        self.generate_report()
        self.print_summary()
        
        return self.results['failed'] == 0
    
    def run_compliance_scan(self):
        """Run compliance scanning for core modules"""
        print("\n🔍 Running Core Module Compliance Scan...")
        
        compliance_results = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'checks': {},
            'total_checks': 0,
            'passed_checks': 0,
            'failed_checks': 0
        }
        
        # Check core module compliance
        core_checks = [
            ('Authentication System', self.check_auth_compliance),
            ('Compliance Module', self.check_compliance_module_compliance),
            ('Analysis Module', self.check_analysis_module_compliance),
            ('Blockchain Module', self.check_blockchain_module_compliance),
            ('Data Protection', self.check_data_protection_compliance),
            ('Audit Logging', self.check_audit_logging_compliance),
            ('Access Control', self.check_access_control_compliance),
            ('Regulatory Reporting', self.check_regulatory_reporting_compliance)
        ]
        
        for check_name, check_func in core_checks:
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
        compliance_file = self.results_dir / 'core_compliance_scan.json'
        with open(compliance_file, 'w') as f:
            json.dump(compliance_results, f, indent=2)
        
        print(f"\n📊 Core Module Compliance Scan Results:")
        print(f"   Total Checks: {compliance_results['total_checks']}")
        print(f"   Passed: {compliance_results['passed_checks']}")
        print(f"   Failed: {compliance_results['failed_checks']}")
        
        return compliance_results['failed_checks'] == 0
    
    def check_auth_compliance(self):
        """Check authentication system compliance"""
        issues = []
        
        # Check auth module exists
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
                if 'password_hash' not in auth_content:
                    issues.append("Password hashing not implemented")
        except Exception:
            issues.append("Cannot read authentication module")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_compliance_module_compliance(self):
        """Check compliance module compliance"""
        issues = []
        
        # Check compliance module exists
        compliance_dir = self.project_root / 'src' / 'compliance'
        if not compliance_dir.exists():
            issues.append("Compliance module not found")
        
        # Check compliance features (actual existing files)
        compliance_files = [
            self.project_root / 'src' / 'compliance' / 'regulatory_reporting.py',
            self.project_root / 'src' / 'compliance' / 'case_management.py',
            self.project_root / 'src' / 'compliance' / 'audit_trail.py',
            self.project_root / 'src' / 'compliance' / 'automated_risk_assessment.py'
        ]
        
        for file_path in compliance_files:
            if not file_path.exists():
                issues.append(f"Compliance component not found: {file_path.name}")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_analysis_module_compliance(self):
        """Check analysis module compliance"""
        issues = []
        
        # Check analysis module exists
        analysis_dir = self.project_root / 'src' / 'analysis'
        if not analysis_dir.exists():
            issues.append("Analysis module not found")
        
        # Check ML model security
        ml_files = [
            self.project_root / 'src' / 'analysis' / 'ml_risk_model.py',
            self.project_root / 'src' / 'analysis' / 'pattern_detection.py'
        ]
        
        for file_path in ml_files:
            if not file_path.exists():
                issues.append(f"Analysis component not found: {file_path.name}")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_blockchain_module_compliance(self):
        """Check blockchain module compliance"""
        issues = []
        
        # Check blockchain module exists
        blockchain_dir = self.project_root / 'src' / 'collectors' / 'rpc'
        if not blockchain_dir.exists():
            issues.append("Blockchain RPC module not found")
        
        # Check RPC clients
        rpc_files = [
            self.project_root / 'src' / 'collectors' / 'rpc' / 'solana_rpc.py',
            self.project_root / 'src' / 'collectors' / 'rpc' / 'tron_rpc.py',
            self.project_root / 'src' / 'collectors' / 'rpc' / 'xrpl_rpc.py'
        ]
        
        for file_path in rpc_files:
            if not file_path.exists():
                issues.append(f"RPC client not found: {file_path.name}")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_data_protection_compliance(self):
        """Check data protection compliance"""
        issues = []
        
        # Check data protection features (actual existing files)
        protection_files = [
            self.project_root / 'src' / 'database' / 'gdpr_compliance.py',
            self.project_root / 'src' / 'utils' / 'encryption.py'
        ]
        
        for file_path in protection_files:
            if not file_path.exists():
                issues.append(f"Data protection component not found: {file_path.name}")
        
        # Check if GDPR compliance has encryption functionality
        gdpr_file = self.project_root / 'src' / 'database' / 'gdpr_compliance.py'
        if gdpr_file.exists():
            try:
                with open(gdpr_file, 'r') as f:
                    gdpr_content = f.read()
                    if 'Fernet' not in gdpr_content:
                        issues.append("GDPR compliance missing encryption functionality")
                    if 'encrypt' not in gdpr_content:
                        issues.append("GDPR compliance missing encryption methods")
            except Exception:
                issues.append("Cannot read GDPR compliance file")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_audit_logging_compliance(self):
        """Check audit logging compliance"""
        issues = []
        
        # Check audit logging implementation (actual existing files)
        audit_files = [
            self.project_root / 'src' / 'compliance' / 'audit_trail.py',
            self.project_root / 'src' / 'monitoring' / 'compliance_monitoring.py',
            self.project_root / 'src' / 'monitoring' / 'audit.py',
            self.project_root / 'src' / 'api' / 'middleware.py'
        ]
        
        for file_path in audit_files:
            if not file_path.exists():
                issues.append(f"Audit logging component not found: {file_path.name}")
        
        # Check if audit trail has comprehensive functionality
        audit_trail_file = self.project_root / 'src' / 'compliance' / 'audit_trail.py'
        if audit_trail_file.exists():
            try:
                with open(audit_trail_file, 'r') as f:
                    audit_content = f.read()
                    if 'AuditTrailEngine' not in audit_content:
                        issues.append("Audit trail missing AuditTrailEngine")
                    if 'AuditEvent' not in audit_content:
                        issues.append("Audit trail missing AuditEvent class")
            except Exception:
                issues.append("Cannot read audit trail file")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_access_control_compliance(self):
        """Check access control compliance"""
        issues = []
        
        # Check access control implementation
        auth_file = self.project_root / 'src' / 'api' / 'auth.py'
        try:
            with open(auth_file, 'r') as f:
                auth_content = f.read()
                if 'PERMISSIONS' not in auth_content:
                    issues.append("Permission constants not defined")
                if 'check_permissions' not in auth_content:
                    issues.append("Permission checking not implemented")
        except Exception:
            issues.append("Cannot read access control implementation")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def check_regulatory_reporting_compliance(self):
        """Check regulatory reporting compliance"""
        issues = []
        
        # Check regulatory reporting features (actual existing files)
        reporting_files = [
            self.project_root / 'src' / 'compliance' / 'regulatory_reporting.py',
            self.project_root / 'src' / 'export' / 'compliance_export.py'
        ]
        
        for file_path in reporting_files:
            if not file_path.exists():
                issues.append(f"Regulatory reporting component not found: {file_path.name}")
        
        # Check if regulatory reporting has comprehensive functionality
        regulatory_file = self.project_root / 'src' / 'compliance' / 'regulatory_reporting.py'
        if regulatory_file.exists():
            try:
                with open(regulatory_file, 'r') as f:
                    regulatory_content = f.read()
                    if 'RegulatoryReportingEngine' not in regulatory_content:
                        issues.append("Regulatory reporting missing RegulatoryReportingEngine")
                    if 'RegulatoryReport' not in regulatory_content:
                        issues.append("Regulatory reporting missing RegulatoryReport class")
            except Exception:
                issues.append("Cannot read regulatory reporting file")
        
        return {'passed': len(issues) == 0, 'issues': issues}
    
    def generate_report(self):
        """Generate comprehensive core security test report"""
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
        report_file = self.results_dir / 'core_security_test_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Core security test report saved to: {report_file}")
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("🔒 CORE SECURITY TEST SUMMARY (PHASES 1-3)")
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
            print(f"\n✅ All core security tests passed!")
            return True


def main():
    parser = argparse.ArgumentParser(description='Run Jackdaw Sentry core security tests')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--compliance-only', action='store_true', help='Run compliance scan only')
    parser.add_argument('--module', '-m', help='Run specific module tests (compliance|analysis|blockchain|auth)')
    
    args = parser.parse_args()
    
    runner = CoreSecurityTestRunner()
    
    if args.compliance_only:
        success = runner.run_compliance_scan()
    elif args.module:
        success = runner.run_module_specific_tests(args.module, args.verbose)
    else:
        success = runner.run_all_tests(args.verbose)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
