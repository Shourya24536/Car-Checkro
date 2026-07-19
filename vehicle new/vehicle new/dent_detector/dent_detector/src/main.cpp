#include <iostream>
#include <opencv2/opencv.hpp>
#include "camera.h"
#include "preprocess.h"
#include "led_detector.h"
#include "reference.h"

int main(int argc, char* argv[])
{
    // Default camera source: OnePlus AI Camera Gateway MJPEG relay.
    //
    // The OnePlus phone filters out blurry / over-exposed / glare-affected
    // frames and re-streams only the accepted frames as MJPEG on port 8090.
    // Point this at that relay so inference runs on clean frames.
    //
    // Override at runtime:
    //   ./dent_detector http://192.168.1.200:8090/stream   <- OnePlus relay
    //   ./dent_detector http://192.168.1.100:8080/video    <- Samsung S23 direct
    //   ./dent_detector 0                                  <- local webcam
    std::string url = "http://192.168.1.200:8090/stream";
    if (argc > 1)
    {
        url = argv[1];
    }

    Camera camera(url);
    if (!camera.open())
    {
        std::cerr << "Failed to open camera stream: " << url << std::endl;
        return -1;
    }

    std::cout << "Camera stream opened successfully: " << url << std::endl;

    ReferenceProfile refProfile;
    std::string refPath = "../data/reference.yml";
    bool calibrationDone = false;

    // Load and validate reference profile if it exists
    if (loadReference(refPath, refProfile))
    {
        std::cout << "Successfully loaded reference profile from: " << refPath << std::endl;
        calibrationDone = true;
    }
    else
    {
        std::cout << "Reference file not found or invalid. Entering CALIBRATION Mode." << std::endl;
    }

    cv::Mat frame;
    int frameCount = 0;
    std::vector<std::vector<cv::Point>> calibrationProfiles;
    CalibrationSettings calSettings;

    calSettings.imageWidth = 0;
    calSettings.imageHeight = 0;
    calSettings.roiTop = 0;
    calSettings.roiBottom = 0;
    calSettings.threshold = 0;

    while (true)
    {
        if (!camera.getFrame(frame))
        {
            std::cout << "Failed to grab frame!" << std::endl;
            break;
        }

        frameCount++;

        // Process every 5th frame to manage CPU load on embedded targets
        if (frameCount % 5 == 0)
        {
            std::string rawFilename = "frame_" + std::to_string(frameCount) + ".jpg";
            cv::imwrite(rawFilename, frame);

            if (!calibrationDone)
            {
                // Calibration Mode: Crop bottom 35% of the frame
                cv::Rect roi(
                    0,
                    frame.rows * 0.65,
                    frame.cols,
                    frame.rows * 0.35
                );

                cv::Mat cropped = frame(roi);
                cv::imwrite("../data/cropped.jpg", cropped);

                cv::Mat binary = preprocessImage(cropped);
                cv::Mat profileImage;

                std::vector<cv::Point> profile = extractReflectionProfile(binary, profileImage);
                calibrationProfiles.push_back(profile);

                std::cout << "Calibration Frame " << calibrationProfiles.size() << "/20" << std::endl;
                cv::imwrite("../data/profile.jpg", profileImage);

                if (calibrationProfiles.size() == 20)
                {
                    calSettings.imageWidth = frame.cols;
                    calSettings.imageHeight = frame.rows;
                    calSettings.roiTop = roi.y;
                    calSettings.roiBottom = roi.y + roi.height;
                    calSettings.threshold = 0;

                    if (createReference(calibrationProfiles, calSettings, refPath))
                    {
                        std::cout << "Calibration Complete!" << std::endl;
                        // Transition directly to detection mode
                        if (loadReference(refPath, refProfile))
                        {
                            calibrationDone = true;
                            std::cout << "Reference loaded. Transitioned to DETECTION Mode." << std::endl;
                        }
                        else
                        {
                            std::cerr << "Failed to load reference file after calibration." << std::endl;
                            break;
                        }
                    }
                    else
                    {
                        std::cerr << "Failed to create reference file." << std::endl;
                        break;
                    }
                }
            }
            else
            {
                // Dent Detection Mode: Ensure frame dimensions match reference calibration
                if (frame.cols != refProfile.settings.imageWidth || frame.rows != refProfile.settings.imageHeight)
                {
                    cv::resize(frame, frame, cv::Size(refProfile.settings.imageWidth, refProfile.settings.imageHeight));
                }

                // Crop using ROI bounds from reference file
                cv::Rect roi(
                    0,
                    refProfile.settings.roiTop,
                    refProfile.settings.imageWidth,
                    refProfile.settings.roiBottom - refProfile.settings.roiTop
                );

                cv::Mat cropped = frame(roi);
                cv::imwrite("../data/cropped.jpg", cropped);

                // Start processing timer
                int64 t_start = cv::getTickCount();

                // Preprocess and extract profile
                cv::Mat binary = preprocessImage(cropped);
                cv::imwrite("../data/binary.jpg", binary);

                cv::Mat profileImage;
                std::vector<cv::Point> currentProfile = extractReflectionProfile(binary, profileImage);
                cv::imwrite("../data/profile.jpg", profileImage);

                // Align profile
                std::vector<cv::Point> alignedProfile;
                double dx = 0, dy = 0, slope = 0;
                alignProfiles(currentProfile, refProfile.profile, alignedProfile, dx, dy, slope);

                // Compare and detect dents
                InspectionResult result = analyzeProfile(alignedProfile, refProfile.profile, refProfile.stdDeviation);
                result.alignmentDx = dx;
                result.alignmentDy = dy;
                result.alignmentSlope = slope;

                // Calculate profile completeness
                int nativeCount = 0;
                for (int x = 0; x < binary.cols; ++x)
                {
                    for (int y = 0; y < binary.rows; ++y)
                    {
                        if (binary.at<uchar>(y, x) > 0)
                        {
                            nativeCount++;
                            break;
                        }
                    }
                }
                result.completeness = static_cast<double>(nativeCount) / binary.cols;

                // Calculate processing time
                double t_elapsed = (cv::getTickCount() - t_start) * 1000.0 / cv::getTickFrequency();
                result.processingTimeMs = t_elapsed;

                // Visualize results
                cv::Mat visImage = cropped.clone();
                visualizeInspection(visImage, refProfile.profile, alignedProfile, result);
                cv::imwrite("../data/detection.jpg", visImage);

                // Output stats and json
                printStatistics(result);
                saveInspectionJson("../data/inspection.json", result);
            }
        }
    }

    camera.release();
    return 0;
}
