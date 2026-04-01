"""
Signal processing and calculation logic for the soft shell calculator.

This module contains all numerical computation extracted from the TU Delft script
that cannot be expressed as a simple property of a domain model. Functions in this
module are pure: they take data arrays and parameters as input and return results.
They have no dependency on UI, file I/O, or domain models.

File parsing and field access belong in RPDMeasurement.from_rgp_file. The functions
here receive the already-loaded signal data and resolution as arguments.

Functions to be implemented:

    filter_signal(drill_amp, resolution)
        Apply threshold filtering to remove near-zero samples before the drill enters
        the wood (Step 2 of the pipeline). Returns the filtered signal and the cut depth.

    trim_signal(filtered_signal)
        Apply variance-based trimming using 25-sample windows to isolate the wood
        cross-section signal (Step 3). Returns the pile signal.

    compute_overlap_position(drill_amp, threshold_cut, resolution)
        Find the position in the original signal where variance becomes significant,
        used to align the original and trimmed signals for plotting (Step 4).

    estimate_diameter(pile_signal, resolution)
        Estimate the pile diameter in mm from the length of the trimmed signal (Step 5).

    compute_moving_average(pile_signal)
        Compute a symmetric 100-sample moving average over the pile signal,
        with shortened windows at the edges (Step 6). Returns the movav array.

    count_annual_rings(pile_signal, resolution)
        Smooth the pile signal with a Savitzky-Golay filter and count peaks to estimate
        the number of annual growth rings (Step 7). Returns the ring count.

    estimate_growth_rate(pile_signal, diameter, resolution)
        Estimate the radial growth rate in mm/ring using peak counting in the outer 75%
        zone on each side of the pith (Step 8). Returns the growth rate in mm/ring.

    estimate_sapwood_width(growth_rate, rings)
        Apply the empirical biological regression formula to estimate sapwood width
        in mm from growth rate and ring count (Step 9).

    detect_soft_shell(movav, diameter, resolution)
        Compute the IOMA (Incremental One-directional Moving Average) from the pith
        outward on each side and identify the positions where the moving average falls
        below 40% of the maximum IOMA value (Step 10). Returns soft shell thickness
        in mm for the left and right sides.
"""
