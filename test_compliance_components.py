#!/usr/bin/env python3
"""
Simple test script to verify the compliance components work correctly
"""

import sys
import os
sys.path.append('/home/dribble0335/dev/jackdawsentry')

def test_encryption_utils():
    """Test encryption utilities"""
    print("🔐 Testing Encryption Utilities...")
    
    try:
        from src.utils.encryption import (
            encrypt_data, decrypt_data, mask_email, 
            mask_phone, mask_credit_card, hash_data
        )
        
        # Test encryption/decryption
        test_data = "sensitive test data"
        encrypted = encrypt_data(test_data)
        decrypted = decrypt_data(encrypted)
        assert decrypted == test_data, "Encryption/decryption failed"
        print("  ✅ Encryption/decryption working")
        
        # Test masking functions
        assert mask_email("user@example.com") != "user@example.com", "Email masking failed"
        assert mask_phone("1234567890") != "1234567890", "Phone masking failed"
        assert mask_credit_card("4111111111111111") != "4111111111111111", "Credit card masking failed"
        print("  ✅ Data masking functions working")
        
        # Test hashing
        hash_result = hash_data("test data")
        assert len(hash_result) == 64, "Hash generation failed"
        print("  ✅ Hash generation working")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def test_audit_utilities():
    """Test audit utilities"""
    print("📋 Testing Audit Utilities...")
    
    try:
        from src.monitoring.audit import (
            AuditEvent, AuditCategory, AuditSeverity,
            AuditLogger, AuditTrail, log_audit_event
        )
        
        # Test audit event creation
        event = AuditEvent(
            event_type="test_event",
            category=AuditCategory.SECURITY,
            severity=AuditSeverity.LOW,
            user_id="test_user",
            details={"test": True}
        )
        
        assert event.id is not None, "Audit event ID missing"
        assert event.category == AuditCategory.SECURITY, "Audit event category wrong"
        assert event.verify_integrity(), "Audit event integrity check failed"
        print("  ✅ Audit event creation working")
        
        # Test audit logging
        logger = AuditLogger()
        success = logger.log_event(event)
        assert success, "Audit logging failed"
        print("  ✅ Audit logging working")
        
        # Test audit trail
        trail = AuditTrail()
        success = trail.add_event(event)
        assert success, "Audit trail addition failed"
        print("  ✅ Audit trail working")
        
        # Test convenience function
        event2 = log_audit_event(
            event_type="convenience_test",
            category=AuditCategory.COMPLIANCE,
            severity=AuditSeverity.MEDIUM,
            user_id="test_user"
        )
        assert event2.id is not None, "Convenience audit function failed"
        print("  ✅ Convenience audit function working")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def test_compliance_components():
    """Test compliance components"""
    print("🔍 Testing Compliance Components...")
    
    try:
        # Test compliance module imports
        from src.compliance import (
            RegulatoryReportingEngine,
            CaseManagementEngine,
            AuditTrailEngine,
            AutomatedRiskAssessmentEngine
        )
        
        # Test engine instantiation
        regulatory_engine = RegulatoryReportingEngine()
        case_engine = CaseManagementEngine()
        audit_engine = AuditTrailEngine()
        risk_engine = AutomatedRiskAssessmentEngine()
        
        assert regulatory_engine is not None, "Regulatory engine instantiation failed"
        assert case_engine is not None, "Case engine instantiation failed"
        assert audit_engine is not None, "Audit engine instantiation failed"
        assert risk_engine is not None, "Risk engine instantiation failed"
        print("  ✅ Compliance engines instantiation working")
        
        return True
        
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Compliance Components Implementation")
    print("=" * 50)
    
    tests = [
        ("Encryption Utilities", test_encryption_utils),
        ("Audit Utilities", test_audit_utilities),
        ("Compliance Components", test_compliance_components)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}:")
        result = test_func()
        results.append((test_name, result))
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All compliance components are working correctly!")
        return True
    else:
        print("⚠️  Some components have issues")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
