# Svensson Estimates App

This Django app manages Svensson model parameter estimation according to ANBIMA's method for Brazilian interest rate curves.

## Overview

The Svensson model is used to estimate the term structure of interest rates. This app provides:
- Storage of parameter estimation attempts
- Visualization of B3 rate data points
- Interface for analyzing estimation results

## Models

### LinearAttempt

Stores the parameters of a linear attempt to arrive at the Svensson model parameters.

**Fields:**
- `date` - Date associated with this estimation attempt
- `beta0_initial`, `beta1_initial`, `beta2_initial`, `beta3_initial` - Initial β parameters
- `lambda1_initial`, `lambda2_initial` - Initial λ parameters
- `beta0_final`, `beta1_final`, `beta2_final`, `beta3_final` - Final β parameters (after estimation)
- `lambda1_final`, `lambda2_final` - Final λ parameters (after estimation)
- `observation` - Notes about the estimation attempt
- `created_at`, `updated_at` - Metadata timestamps

## Views

### Homepage (`/svensson/`)

The main interface provides:
- **Right Sidebar**: List of available dates (from B3Rate data), newest first
- **Main Area**: Interactive chart showing DI x PRÉ 252 rate curve for selected date
- **Chart Features**:
  - Drag to zoom into specific area
  - Scroll for quick zoom
  - Ctrl+drag to pan
  - Reset zoom button

## Usage

1. First, ensure you have B3 rate data imported via the main rates app
2. Navigate to `/svensson/` or use the link from the rates homepage
3. Select a date from the sidebar to visualize its rate curve
4. Use the interactive chart to analyze the data points

## Integration

The app integrates with the `rates` app:
- Uses B3Rate model for date listings and rate data
- Accessible via link from the rates homepage

## Future Enhancements

This app is designed to support:
- Parameter estimation algorithms
- Comparison of multiple estimation attempts
- Visualization of fitted curves vs actual data points
- Historical analysis of parameter evolution

