#!/usr/bin/env python3
"""
Simple test script for ZParameterEditor plugin
This script tests the basic functionality without requiring Cura runtime
"""

import json
import sys
import os

# Add the plugin directory to Python path
plugin_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, plugin_dir)

def test_parameter_data_format():
    """Test parameter data format conversion"""
    print("Testing parameter data format...")
    
    # Sample parameter data
    parameter_data = [
        {"height": 0.0, "value": 200.0},
        {"height": 10.0, "value": 210.0},
        {"height": 20.0, "value": 205.0}
    ]
    
    # Convert to CuraEngine format
    formatted_data = [[point["height"], point["value"]] for point in parameter_data]
    json_data = json.dumps(formatted_data)
    
    expected = "[[0.0, 200.0], [10.0, 210.0], [20.0, 205.0]]"
    
    print(f"Input data: {parameter_data}")
    print(f"Formatted: {json_data}")
    print(f"Expected: {expected}")
    print(f"Test passed: {json_data == expected}")
    print()

def test_parameter_types():
    """Test parameter type definitions"""
    print("Testing parameter type definitions...")
    
    parameter_types = {
        "temperature": {
            "label": "Temperature Profile",
            "setting_key": "user_temperature_definition",
            "enable_key": "user_temperature_definition_enable",
            "unit": "°C",
            "min_value": 150,
            "max_value": 300,
            "default_value": 200
        },
        "speed_ratio": {
            "label": "Speed Ratio Profile", 
            "setting_key": "user_speed_ratio_definition",
            "enable_key": "user_speed_ratio_definition_enable",
            "unit": "%",
            "min_value": 10,
            "max_value": 200,
            "default_value": 100
        }
    }
    
    for param_type, config in parameter_types.items():
        print(f"Parameter type: {param_type}")
        print(f"  Label: {config['label']}")
        print(f"  Setting key: {config['setting_key']}")
        print(f"  Enable key: {config['enable_key']}")
        print(f"  Unit: {config['unit']}")
        print(f"  Range: {config['min_value']} - {config['max_value']}")
        print(f"  Default: {config['default_value']}")
        print()

def test_point_insertion():
    """Test parameter point insertion logic"""
    print("Testing parameter point insertion...")
    
    data = []
    
    def add_parameter_point(height, value):
        """Simulate the addParameterPoint method"""
        point = {"height": float(height), "value": float(value)}
        
        # Find insertion point
        insert_index = 0
        for i, existing_point in enumerate(data):
            if existing_point["height"] > height:
                insert_index = i
                break
            elif existing_point["height"] == height:
                # Replace existing point at same height
                data[i] = point
                return
            else:
                insert_index = i + 1
                
        data.insert(insert_index, point)
    
    # Test insertion
    add_parameter_point(10.0, 210.0)
    add_parameter_point(0.0, 200.0)
    add_parameter_point(20.0, 205.0)
    add_parameter_point(5.0, 208.0)
    add_parameter_point(10.0, 215.0)  # Should replace existing point
    
    print("Final data (should be sorted by height):")
    for point in data:
        print(f"  Height: {point['height']}, Value: {point['value']}")
    
    # Verify sorting
    heights = [point["height"] for point in data]
    is_sorted = heights == sorted(heights)
    print(f"Data is sorted: {is_sorted}")
    print()

def test_model_height_calculation():
    """Test model height and layer calculations"""
    print("Testing model height calculations...")
    
    model_height = 25.6
    layer_height = 0.2
    total_layers = model_height / layer_height
    
    print(f"Model height: {model_height} mm")
    print(f"Layer height: {layer_height} mm")
    print(f"Total layers: {total_layers} ({int(total_layers)} complete layers)")
    print(f"Ceiling layers: {int(model_height // layer_height + (1 if model_height % layer_height > 0 else 0))}")
    print()

def main():
    """Run all tests"""
    print("ZParameterEditor Plugin Test Suite")
    print("=" * 40)
    print()
    
    test_parameter_data_format()
    test_parameter_types()
    test_point_insertion()
    test_model_height_calculation()
    
    print("All tests completed!")

if __name__ == "__main__":
    main()
