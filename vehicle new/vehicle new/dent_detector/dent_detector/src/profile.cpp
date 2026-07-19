#include "profile.h"
#include <fstream>
#include <iostream>

void saveProfile(
    const std::vector<cv::Point>& profile,
    const std::string& filename)
{
    cv::FileStorage fs(filename, cv::FileStorage::WRITE);
    if (!fs.isOpened())
    {
        std::cerr << "Failed to save profile to " << filename << std::endl;
        return;
    }
    fs << "profile" << profile;
    fs.release();
}

std::vector<cv::Point> loadProfile(
    const std::string& filename)
{
    std::vector<cv::Point> profile;
    cv::FileStorage fs(filename, cv::FileStorage::READ);
    if (!fs.isOpened())
    {
        std::cerr << "Failed to load profile from " << filename << std::endl;
        return profile;
    }
    fs["profile"] >> profile;
    fs.release();
    return profile;
}
