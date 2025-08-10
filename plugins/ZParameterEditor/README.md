# Z Parameter Editor

A Cura plugin that provides a visual interface for editing Z-height dependent parameters like temperature and speed profiles.

## Features

- **Visual Parameter Editing**: Interactive graph interface for defining parameter curves
- **Multiple Parameter Types**: Support for temperature profiles and speed ratio profiles
- **Click-to-Add**: Click on the graph to add parameter points at specific heights and values
- **Real-time Preview**: See your parameter curve as you build it
- **Model Integration**: Automatically detects model height and layer settings
- **Easy Management**: Add, remove, and clear parameter points with simple controls

## Supported Parameters

### Temperature Profile
- Controls: `user_temperature_definition` and `user_temperature_definition_enable`
- Range: 150°C - 300°C
- Use case: Adjust printing temperature at different heights for optimal material properties

### Speed Ratio Profile  
- Controls: `user_speed_ratio_definition` and `user_speed_ratio_definition_enable`
- Range: 10% - 200%
- Use case: Modify printing speed at different heights for quality optimization

## How to Use

1. **Select Parameter Type**: Choose between Temperature or Speed using the toolbar buttons
2. **Add Points**: 
   - Click directly on the graph to set height and value
   - Or use the input fields and click "Add"
3. **Edit Points**: Click on existing points to remove them
4. **Apply Settings**: Click "Apply to Settings" to activate the parameter profile in Cura

## Interface Elements

- **Graph Area**: Visual representation of your parameter curve
  - Vertical axis: Z height (mm)
  - Horizontal axis: Parameter value (°C or %)
  - Blue dots: Parameter control points
- **Quick Controls**: Input fields for precise value entry
- **Point List**: Shows all defined parameter points
- **Model Info**: Displays current model height and layer settings

## Installation

1. Copy the `ZParameterEditor` folder to your Cura plugins directory
2. Restart Cura
3. The tool will appear in the left toolbar

## Technical Details

The plugin generates parameter data in the format expected by CuraEngine:
```
[[height1, value1], [height2, value2], ...]
```

This data is applied to the corresponding Cura settings:
- `user_temperature_definition` for temperature profiles
- `user_speed_ratio_definition` for speed ratio profiles

## Requirements

- Cura 5.0 or later
- Compatible CuraEngine with Z-parameter support

## Author

wsd - 2024
