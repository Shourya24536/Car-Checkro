#ifndef LED_DETECTOR_H
#define LED_DETECTOR_H

#include <opencv2/opencv.hpp>
#include <vector>
#include <string>

struct Dent {
    int start;
    int end;
    int center;
    int width;
    double depth;
    std::string severity;
    double confidence;
};

struct InspectionResult {
    bool hasDent;
    std::vector<Dent> dents;
    double rmse;
    double avgDeviation;
    double maxDeviation;
    double noiseLevel;
    double alignmentDx;
    double alignmentDy;
    double alignmentSlope;
    double completeness;
    double processingTimeMs;
};

// Milestone 1, 8, 9: Modular profile processing
std::vector<cv::Point> extractReflectionProfile(
    const cv::Mat& binary,
    cv::Mat& output
);

void rejectOutliers(std::vector<int>& y_values, int threshold = 15);
void fillMissing(std::vector<int>& y_values);
void medianFilter(std::vector<int>& y_values, int windowSize = 5);
void movingAverage(std::vector<int>& y_values, int windowSize = 5);

// Milestone 3: Profile Alignment
void alignProfiles(
    const std::vector<cv::Point>& current,
    const std::vector<cv::Point>& reference,
    std::vector<cv::Point>& aligned,
    double& dx,
    double& dy,
    double& slope
);

// Milestone 4, 5: Comparison and Detection
InspectionResult analyzeProfile(
    const std::vector<cv::Point>& aligned,
    const std::vector<cv::Point>& reference,
    const double refStdDev
);

// Milestone 6: Visualization
void visualizeInspection(
    cv::Mat& output,
    const std::vector<cv::Point>& reference,
    const std::vector<cv::Point>& aligned,
    const InspectionResult& result
);

// Milestone 7: Statistics & JSON Output
void printStatistics(const InspectionResult& result);
void saveInspectionJson(const std::string& filename, const InspectionResult& result);

#endif

