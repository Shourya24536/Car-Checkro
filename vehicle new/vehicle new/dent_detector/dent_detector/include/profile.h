#ifndef PROFILE_H
#define PROFILE_H

#include <opencv2/opencv.hpp>
#include <vector>
#include <string>

void saveProfile(
    const std::vector<cv::Point>& profile,
    const std::string& filename
);

std::vector<cv::Point> loadProfile(
    const std::string& filename
);

#endif

