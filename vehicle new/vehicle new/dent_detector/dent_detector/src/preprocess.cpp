#include "preprocess.h"

cv::Mat preprocessImage(const cv::Mat& frame)
{
    cv::Mat blurred;
    cv::GaussianBlur(frame, blurred, cv::Size(5,5), 0);

    cv::Mat hsv;
    cv::cvtColor(blurred, hsv, cv::COLOR_BGR2HSV);

    std::vector<cv::Mat> channels;
    cv::split(hsv, channels);

    cv::Mat value = channels[2];

    cv::Mat binary;
    cv::threshold(value, binary, 220, 255, cv::THRESH_BINARY);

    cv::Mat kernel =
        cv::getStructuringElement(cv::MORPH_ELLIPSE,
                                  cv::Size(3,3));

    cv::morphologyEx(binary,
                     binary,
                     cv::MORPH_OPEN,
                     kernel);

    return binary;
}
