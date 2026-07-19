#include "camera.h"

Camera::Camera(const std::string& source)
    : source_(source)
{
}

bool Camera::open()
{
    cap_.open(source_);
    return cap_.isOpened();
}

bool Camera::getFrame(cv::Mat& frame)
{
    return cap_.read(frame);
}

void Camera::release()
{
    if (cap_.isOpened())
        cap_.release();
}
