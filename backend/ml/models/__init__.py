# ML Model Artifacts (trained models stored here locally, Azure Blob in prod)
# Structure: {model_name}/v{version}/{model_name}.onnx
# e.g. anomaly_detector/v202602110800/anomaly_detector.onnx
#
# Day-1 models:
#   - anomaly_detector (Isolation Forest)
#   - trending_scorer (Ridge regression on time-series)
#   - confidence_calibrator (Logistic regression)
