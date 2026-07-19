#include "reference.h"

#include <opencv2/opencv.hpp>
#include <cmath>
#include <iostream>

using namespace cv;
using namespace std;

//----------------------------------------------------
// Compute Mean
//----------------------------------------------------
static double computeMean(const vector<Point>& profile)
{
    if(profile.empty())
        return 0.0;

    double sum = 0.0;

    for(const auto& p : profile)
        sum += p.y;

    return sum / profile.size();
}

//----------------------------------------------------
// Compute Standard Deviation
//----------------------------------------------------
static double computeStdDev(
    const vector<Point>& profile,
    double mean)
{
    if(profile.empty())
        return 0.0;

    double sum = 0.0;

    for(const auto& p : profile)
    {
        double diff = p.y - mean;
        sum += diff * diff;
    }

    return sqrt(sum / profile.size());
}

//----------------------------------------------------
// Create Reference
//----------------------------------------------------
bool createReference(
    const vector<vector<Point>>& profiles,
    const CalibrationSettings& settings,
    const string& filename)
{
    if(profiles.empty())
    {
        cerr << "No profiles received." << endl;
        return false;
    }

    size_t profileSize = profiles[0].size();

    for(const auto& profile : profiles)
    {
        if(profile.size() != profileSize)
        {
            cerr << "Profile size mismatch." << endl;
            return false;
        }
    }

    vector<Point> averageProfile;
    averageProfile.reserve(profileSize);

    for(size_t i = 0; i < profileSize; i++)
    {
        double sumY = 0.0;

        for(const auto& profile : profiles)
        {
            sumY += profile[i].y;
        }

        int avgY = static_cast<int>(round(sumY / profiles.size()));
        int x = profiles[0][i].x;

        averageProfile.emplace_back(x, avgY);
    }

    double mean = computeMean(averageProfile);
    double stdDev = computeStdDev(averageProfile, mean);

    FileStorage fs(filename, FileStorage::WRITE);

    if(!fs.isOpened())
    {
        cerr << "Cannot create " << filename << endl;
        return false;
    }

    fs << "imageWidth" << settings.imageWidth;
    fs << "imageHeight" << settings.imageHeight;

    fs << "roiTop" << settings.roiTop;
    fs << "roiBottom" << settings.roiBottom;

    fs << "threshold" << settings.threshold;

    fs << "averageY" << mean;
    fs << "stdDeviation" << stdDev;

    fs << "profile" << "[";

    for(const auto& p : averageProfile)
    {
        fs << "{"
           << "x" << p.x
           << "y" << p.y
           << "}";
    }

    fs << "]";

    fs.release();

    cout << "Reference saved to "
         << filename
         << endl;

    return true;
}

//----------------------------------------------------
// Load Reference
//----------------------------------------------------
bool loadReference(
    const string& filename,
    ReferenceProfile& reference)
{
    FileStorage fs(filename, FileStorage::READ);

    if(!fs.isOpened())
    {
        cerr << "Cannot open reference file: "
             << filename << endl;
        return false;
    }

    // 1. Load Metadata
    try {
        fs["imageWidth"] >> reference.settings.imageWidth;
        fs["imageHeight"] >> reference.settings.imageHeight;
        fs["roiTop"] >> reference.settings.roiTop;
        fs["roiBottom"] >> reference.settings.roiBottom;
        fs["threshold"] >> reference.settings.threshold;
        fs["averageY"] >> reference.averageY;
        fs["stdDeviation"] >> reference.stdDeviation;
    } catch (const cv::Exception& e) {
        cerr << "Error: Reference file '" << filename << "' has missing or malformed metadata: " << e.what() << endl;
        fs.release();
        return false;
    }

    // 2. Validate Metadata
    if (reference.settings.imageWidth <= 0 || reference.settings.imageHeight <= 0)
    {
        cerr << "Validation Error: Invalid image dimensions in reference file ("
             << reference.settings.imageWidth << "x" << reference.settings.imageHeight << ")." << endl;
        fs.release();
        return false;
    }

    if (reference.settings.roiTop < 0 || 
        reference.settings.roiBottom > reference.settings.imageHeight || 
        reference.settings.roiTop >= reference.settings.roiBottom)
    {
        cerr << "Validation Error: Invalid ROI configuration in reference file ("
             << "roiTop=" << reference.settings.roiTop 
             << ", roiBottom=" << reference.settings.roiBottom 
             << ", imageHeight=" << reference.settings.imageHeight << ")." << endl;
        fs.release();
        return false;
    }

    if (reference.averageY < 0.0 || reference.stdDeviation < 0.0)
    {
        cerr << "Validation Error: Invalid profile statistics in reference file ("
             << "averageY=" << reference.averageY 
             << ", stdDeviation=" << reference.stdDeviation << ")." << endl;
        fs.release();
        return false;
    }

    // 3. Load Profile Points
    reference.profile.clear();
    FileNode points = fs["profile"];
    if (points.type() != FileNode::SEQ)
    {
        cerr << "Validation Error: 'profile' key in reference file is not a sequence." << endl;
        fs.release();
        return false;
    }

    int expected_size = reference.settings.imageWidth;
    int idx = 0;

    for(auto it = points.begin(); it != points.end(); ++it, ++idx)
    {
        int x = -1, y = -1;
        try {
            (*it)["x"] >> x;
            (*it)["y"] >> y;
        } catch (const cv::Exception& e) {
            cerr << "Validation Error: Failed to parse point at index " << idx << " in reference profile." << endl;
            fs.release();
            return false;
        }

        // Validate Point range
        if (x != idx)
        {
            cerr << "Validation Error: Profile x-coordinate mismatch at index " << idx 
                 << " (expected " << idx << ", got " << x << ")." << endl;
            fs.release();
            return false;
        }

        int roi_height = reference.settings.roiBottom - reference.settings.roiTop;
        if (y < 0 || y > roi_height)
        {
            cerr << "Validation Error: Profile y-coordinate " << y << " at column " << x 
                 << " is out of ROI bounds [0, " << roi_height << "]." << endl;
            fs.release();
            return false;
        }

        reference.profile.emplace_back(x, y);
    }

    fs.release();

    // 4. Validate Profile Size
    if (static_cast<int>(reference.profile.size()) != expected_size)
    {
        cerr << "Validation Error: Reference profile size (" << reference.profile.size() 
             << ") does not match imageWidth (" << expected_size << ")." << endl;
        return false;
    }

    cout << "Reference file '" << filename << "' successfully loaded and validated ("
         << reference.profile.size() << " points)." << endl;

    return true;
}

