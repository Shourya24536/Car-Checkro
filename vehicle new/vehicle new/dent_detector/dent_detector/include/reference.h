#ifndef REFERENCE_H
#define REFERENCE_H

#include <opencv2/opencv.hpp>
#include <string>
#include <vector>

struct CalibrationSettings
{
    int imageWidth;
    int imageHeight;

    int roiTop;
    int roiBottom;

    int threshold;
};

struct ReferenceProfile
{
    CalibrationSettings settings;

    double averageY;
    double stdDeviation;

    std::vector<cv::Point> profile;
};

bool createReference(
    const std::vector<std::vector<cv::Point>>& profiles,
    const CalibrationSettings& settings,
    const std::string& filename);

bool loadReference(
    const std::string& filename,
    ReferenceProfile& reference);

#endif
