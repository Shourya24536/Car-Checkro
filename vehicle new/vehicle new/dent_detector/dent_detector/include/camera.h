#ifndef CAMERA_H
#define CAMERA_H

#include <opencv2/opencv.hpp>
#include <string>

class Camera {
public:
    Camera(const std::string& source);

    bool open();
    bool getFrame(cv::Mat& frame);
    void release();

private:
    std::string source_;
    cv::VideoCapture cap_;
};

#endif
