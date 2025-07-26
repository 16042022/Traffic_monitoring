# tests/run_tests.py
"""
Test runner for Traffic Monitoring System
Run all tests or specific test suites
"""

import sys
import unittest
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_all_tests():
    """Run all unit tests"""
    loader = unittest.TestLoader()
    start_dir = Path(__file__).parent
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_component_tests():
    """Run only component tests"""
    from test_vehicle_tracker import TestVehicleTracker
    from test_traffic_monitor import TestTrafficMonitor
    from tests.test_anomaly_detector import TestAnomalyDetector
    
    suite = unittest.TestSuite()
    
    # Add component tests
    for test_class in [TestVehicleTracker, TestTrafficMonitor, TestAnomalyDetector]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_repository_tests():
    """Run only repository tests"""
    from test_video_repository import TestVideoRepository
    from test_traffic_data_repository import TestTrafficDataRepository
    from test_anomaly_event_repository import TestAnomalyEventRepository
    
    suite = unittest.TestSuite()
    
    # Add repository tests
    for test_class in [TestVideoRepository, TestTrafficDataRepository, TestAnomalyEventRepository]:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


def run_specific_test(test_name):
    """Run a specific test module"""
    try:
        # Import the test module
        test_module = __import__(f'test_{test_name}', fromlist=[f'Test{test_name.title()}'])
        
        # Get the test class
        test_class_name = f'Test{"".join(word.title() for word in test_name.split("_"))}'
        test_class = getattr(test_module, test_class_name)
        
        # Run tests
        suite = unittest.TestLoader().loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        return result.wasSuccessful()
        
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not find test for '{test_name}'")
        print(f"Available tests: vehicle_tracker, traffic_monitor, anomaly_detector, ")
        print(f"                video_repository, traffic_data_repository, anomaly_event_repository")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run unit tests for Traffic Monitoring System')
    parser.add_argument('--all', action='store_true', help='Run all tests (default)')
    parser.add_argument('--components', action='store_true', help='Run only component tests')
    parser.add_argument('--repositories', action='store_true', help='Run only repository tests')
    parser.add_argument('--test', type=str, help='Run specific test (e.g., vehicle_tracker)')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("Traffic Monitoring System - Unit Tests")
    print("=" * 70)
    
    success = False
    
    if args.test:
        print(f"\nRunning {args.test} tests...\n")
        success = run_specific_test(args.test)
    elif args.components:
        print("\nRunning component tests...\n")
        success = run_component_tests()
    elif args.repositories:
        print("\nRunning repository tests...\n")
        success = run_repository_tests()
    else:
        print("\nRunning all tests...\n")
        success = run_all_tests()
    
    print("\n" + "=" * 70)
    if success:
        print("All tests passed! ✅")
    else:
        print("Some tests failed! ❌")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())