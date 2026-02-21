# Calibration Report v01.2

- dataset size: 8
- default temperature: 1.15
- fitted temperature: 1.05
- NLL (before): 1.163669
- NLL (after): 1.161515
- ECE (before): 0.196573
- ECE (after): 0.179606

## Note
- Temperature scaling calibrates confidence without changing model architecture.
- Runtime overhead is negligible (single scalar operation in softmax temperature).