import unittest
from src.utilities.utils import quantity_buckets


class TestQuantityBuckets(unittest.TestCase):
    def test_risk_on_approach(self):
        """Test risk-on approach where remainder is added to the last bucket"""
        # Test case 1: 5 contracts split into 3 buckets
        result = quantity_buckets(5, 3, "risk_on")
        self.assertEqual(result, [1, 1, 3])
        
        # Test case 2: 10 contracts split into 4 buckets
        result = quantity_buckets(10, 4, "risk_on")
        self.assertEqual(result, [2, 2, 2, 4])
        
        # Test case 3: 7 contracts split into 2 buckets
        result = quantity_buckets(7, 2, "risk_on")
        self.assertEqual(result, [3, 4])

        # Test case 4: 3 contracts split into 1 buckets
        result = quantity_buckets(3, 1, "risk_on")
        self.assertEqual(result, [3])

    def test_risk_off_approach(self):
        """Test risk-off approach where remainder is distributed from the start"""
        # Test case 1: 5 contracts split into 3 buckets
        result = quantity_buckets(5, 3, "risk_off")
        self.assertEqual(result, [2, 2, 1])
        
        # Test case 2: 10 contracts split into 4 buckets
        result = quantity_buckets(10, 4, "risk_off")
        self.assertEqual(result, [3, 3, 3, 1])
        
        # Test case 3: 7 contracts split into 2 buckets
        result = quantity_buckets(7, 2, "risk_off")
        self.assertEqual(result, [4, 3])

        # Test case 4: 3 contracts split into 1 buckets
        result = quantity_buckets(3, 1, "risk_off")
        self.assertEqual(result, [3])
        
    def test_edge_cases(self):
        """Test edge cases of the quantity_buckets function"""
        # Test case 1: Single contract
        result = quantity_buckets(1, 1)
        self.assertEqual(result, [1])
        
        # Test case 2: Equal distribution (no remainder)
        result = quantity_buckets(9, 3)
        self.assertEqual(result, [3, 3, 3])

        # Test case 4: 10 contracts split into 4 buckets
        result = quantity_buckets(8, 4, "risk_on")
        self.assertEqual(result, [2, 2, 2, 2])

        # Test case 4: 10 contracts split into 4 buckets
        result = quantity_buckets(8, 4, "risk_off")
        self.assertEqual(result, [2, 2, 2, 2])
        

    def test_invalid_inputs(self):
        """Test that invalid inputs raise appropriate errors"""
        # Test case 1: Zero position quantity
        with self.assertRaises(ValueError):
            quantity_buckets(0, 3)
            
        # Test case 2: Zero bucket quantity
        with self.assertRaises(ValueError):
            quantity_buckets(5, 0)
            
        # Test case 3: Negative position quantity
        with self.assertRaises(ValueError):
            quantity_buckets(-5, 3)
            
        # Test case 4: Negative bucket quantity
        with self.assertRaises(ValueError):
            quantity_buckets(5, -3)
            
        # Test case 5: Invalid risk approach
        with self.assertRaises(ValueError):
            quantity_buckets(5, 3, "invalid_approach")

        # Test case 5: Invalid risk approach
        with self.assertRaises(ValueError):
            quantity_buckets(5, 9, "risk_on")

    def test_case_insensitivity(self):
        """Test that risk approach is case insensitive"""
        # Test case 1: Uppercase
        result1 = quantity_buckets(5, 3, "RISK_ON")
        result2 = quantity_buckets(5, 3, "risk_on")
        self.assertEqual(result1, result2)
        
        # Test case 2: Mixed case
        result1 = quantity_buckets(5, 3, "RiSk_OfF")
        result2 = quantity_buckets(5, 3, "risk_off")
        self.assertEqual(result1, result2)

if __name__ == '__main__':
    unittest.main()
