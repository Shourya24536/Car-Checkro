#include "led_detector.h"
#include <opencv2/opencv.hpp>
#include <algorithm>
#include <cmath>
#include <iostream>
#include <fstream>
#include <iomanip>

using namespace cv;
using namespace std;

// Helper to draw text with a black outline for better contrast
static void drawTextWithOutline(cv::Mat& img, const string& text, Point org, int fontFace, double fontScale, Scalar color, int thickness)
{
    cv::putText(img, text, org, fontFace, fontScale, Scalar(0, 0, 0), thickness + 2, LINE_AA);
    cv::putText(img, text, org, fontFace, fontScale, color, thickness, LINE_AA);
}

//----------------------------------------------------
// Milestone 1, 8, 9: Modular profile processing
//----------------------------------------------------
std::vector<cv::Point> extractReflectionProfile(
    const cv::Mat& binary,
    cv::Mat& output)
{
    cv::cvtColor(binary, output, cv::COLOR_GRAY2BGR);

    std::vector<int> y_values(binary.cols, -1);
    int prevY = -1;
    const int SEARCH_RADIUS = 12;

    int native_count = 0;

    for (int x = 0; x < binary.cols; x++)
    {
        int bestY = -1;

        if (prevY == -1)
        {
            // Find first white pixel in this column
            for (int y = 0; y < binary.rows; y++)
            {
                if (binary.at<uchar>(y, x) > 0)
                {
                    bestY = y;
                    break;
                }
            }
        }
        else
        {
            int ymin = std::max(0, prevY - SEARCH_RADIUS);
            int ymax = std::min(binary.rows - 1, prevY + SEARCH_RADIUS);

            int longestRun = 0;

            for (int y = ymin; y <= ymax; )
            {
                if (binary.at<uchar>(y, x) == 0)
                {
                    y++;
                    continue;
                }

                int start = y;

                while (y <= ymax && binary.at<uchar>(y, x) > 0)
                {
                    y++;
                }

                int end = y - 1;
                int length = end - start + 1;

                if (length > longestRun)
                {
                    longestRun = length;
                    bestY = (start + end) / 2;
                }
            }
        }

        if (bestY != -1)
        {
            y_values[x] = bestY;
            prevY = bestY;
            native_count++;

            // Draw raw extracted points as small green circles
            cv::circle(output, Point(x, bestY), 1, cv::Scalar(0, 255, 0), -1);
        }
    }

    // Milestone 8: Outlier rejection on raw points before interpolation
    rejectOutliers(y_values, 15);

    // Milestone 1: Fill missing values using linear interpolation
    fillMissing(y_values);

    // Milestone 8: Median filter for salt-and-pepper noise
    medianFilter(y_values, 5);

    // Milestone 8: Moving average smoothing
    movingAverage(y_values, 5);

    // Build the final profile vector
    std::vector<cv::Point> profile;
    profile.reserve(binary.cols);
    for (int x = 0; x < binary.cols; ++x)
    {
        profile.push_back(cv::Point(x, y_values[x]));
    }

    // Draw the final smoothed profile as a continuous yellow line
    for (int x = 1; x < binary.cols; ++x)
    {
        cv::line(output, profile[x - 1], profile[x], cv::Scalar(0, 255, 255), 1);
    }

    return profile;
}

void rejectOutliers(std::vector<int>& y_values, int threshold)
{
    int cols = y_values.size();
    std::vector<int> original = y_values;

    for (int x = 1; x < cols - 1; ++x)
    {
        if (original[x] == -1) continue;

        // Find nearest valid left neighbor (within 10 pixels)
        int left = -1;
        for (int l = x - 1; l >= std::max(0, x - 10); --l)
        {
            if (original[l] != -1)
            {
                left = l;
                break;
            }
        }

        // Find nearest valid right neighbor (within 10 pixels)
        int right = -1;
        for (int r = x + 1; r < std::min(cols, x + 10); ++r)
        {
            if (original[r] != -1)
            {
                right = r;
                break;
            }
        }

        if (left != -1 && right != -1)
        {
            // Interpolate target value
            double t = static_cast<double>(x - left) / (right - left);
            double interp_y = original[left] + t * (original[right] - original[left]);

            if (std::abs(original[x] - interp_y) > threshold)
            {
                y_values[x] = -1; // reject as outlier
            }
        }
    }
}

void fillMissing(std::vector<int>& y_values)
{
    int cols = y_values.size();

    // Find first valid point
    int first_valid = -1;
    for (int x = 0; x < cols; ++x)
    {
        if (y_values[x] != -1)
        {
            first_valid = x;
            break;
        }
    }

    // Fallback: If no valid points found, use center of screen
    if (first_valid == -1)
    {
        std::fill(y_values.begin(), y_values.end(), 120);
        return;
    }

    // Pad left boundary
    for (int x = 0; x < first_valid; ++x)
    {
        y_values[x] = y_values[first_valid];
    }

    // Fill internal gaps and pad right boundary
    int last_valid = first_valid;
    for (int x = first_valid + 1; x < cols; ++x)
    {
        if (y_values[x] != -1)
        {
            if (x - last_valid > 1)
            {
                int left = last_valid;
                int right = x;
                for (int i = left + 1; i < right; ++i)
                {
                    double t = static_cast<double>(i - left) / (right - left);
                    y_values[i] = static_cast<int>(std::round(y_values[left] + t * (y_values[right] - y_values[left])));
                }
            }
            last_valid = x;
        }
    }

    // Pad right boundary from last_valid to the end
    for (int x = last_valid + 1; x < cols; ++x)
    {
        y_values[x] = y_values[last_valid];
    }
}

void medianFilter(std::vector<int>& y_values, int windowSize)
{
    int cols = y_values.size();
    std::vector<int> result = y_values;
    int half = windowSize / 2;

    for (int i = 0; i < cols; ++i)
    {
        std::vector<int> window;
        for (int k = -half; k <= half; ++k)
        {
            int idx = i + k;
            if (idx >= 0 && idx < cols)
            {
                window.push_back(y_values[idx]);
            }
        }
        std::sort(window.begin(), window.end());
        result[i] = window[window.size() / 2];
    }
    y_values = result;
}

void movingAverage(std::vector<int>& y_values, int windowSize)
{
    int cols = y_values.size();
    std::vector<int> result = y_values;
    int half = windowSize / 2;

    for (int i = 0; i < cols; ++i)
    {
        double sum = 0;
        int count = 0;
        for (int k = -half; k <= half; ++k)
        {
            int idx = i + k;
            if (idx >= 0 && idx < cols)
            {
                sum += y_values[idx];
                count++;
            }
        }
        result[i] = static_cast<int>(std::round(sum / count));
    }
    y_values = result;
}

//----------------------------------------------------
// Milestone 3: Profile Alignment (Optimized 1D)
//----------------------------------------------------
void alignProfiles(
    const std::vector<cv::Point>& current,
    const std::vector<cv::Point>& reference,
    std::vector<cv::Point>& aligned,
    double& dx,
    double& dy,
    double& slope)
{
    int N = current.size();
    if (N == 0 || reference.size() != static_cast<size_t>(N))
    {
        aligned = current;
        dx = 0;
        dy = 0;
        slope = 0;
        return;
    }

    double best_mae = 1e9;
    int best_dx = 0;
    double best_dy = 0.0;

    // Search horizontal shifts dx in [-15, 15]
    for (int shift_x = -15; shift_x <= 15; ++shift_x)
    {
        std::vector<double> diffs;
        diffs.reserve(N);
        for (int x = 0; x < N; ++x)
        {
            int curr_x = x + shift_x;
            if (curr_x < 0) curr_x = 0;
            if (curr_x >= N) curr_x = N - 1;

            diffs.push_back(current[curr_x].y - reference[x].y);
        }

        // Robust vertical offset dy estimation using Median
        std::vector<double> diffs_copy = diffs;
        std::nth_element(diffs_copy.begin(), diffs_copy.begin() + N / 2, diffs_copy.end());
        double current_dy = diffs_copy[N / 2];

        // Compute Mean Absolute Error (MAE)
        double mae = 0.0;
        for (double d : diffs)
        {
            mae += std::abs(d - current_dy);
        }
        mae /= N;

        if (mae < best_mae)
        {
            best_mae = mae;
            best_dx = shift_x;
            best_dy = current_dy;
        }
    }

    // Estimate slope (rotation) in O(N) using left-right half medians
    std::vector<double> left_diffs, right_diffs;
    left_diffs.reserve(N / 2);
    right_diffs.reserve(N - N / 2);

    for (int x = 0; x < N; ++x)
    {
        int curr_x = x + best_dx;
        if (curr_x < 0) curr_x = 0;
        if (curr_x >= N) curr_x = N - 1;

        double diff = current[curr_x].y - reference[x].y;
        if (x < N / 2)
        {
            left_diffs.push_back(diff);
        }
        else
        {
            right_diffs.push_back(diff);
        }
    }

    std::nth_element(left_diffs.begin(), left_diffs.begin() + left_diffs.size() / 2, left_diffs.end());
    double median_left = left_diffs[left_diffs.size() / 2];

    std::nth_element(right_diffs.begin(), right_diffs.begin() + right_diffs.size() / 2, right_diffs.end());
    double median_right = right_diffs[right_diffs.size() / 2];

    double estimated_slope = (median_right - median_left) / (N / 2.0);

    // Apply alignment transformation
    dx = best_dx;
    dy = best_dy;
    slope = estimated_slope;

    aligned.clear();
    aligned.reserve(N);
    for (int x = 0; x < N; ++x)
    {
        int curr_x = x + best_dx;
        if (curr_x < 0) curr_x = 0;
        if (curr_x >= N) curr_x = N - 1;

        double aligned_y = current[curr_x].y - best_dy - estimated_slope * (x - N / 2.0);
        aligned.push_back(cv::Point(x, static_cast<int>(std::round(aligned_y))));
    }
}

//----------------------------------------------------
// Milestone 4, 5: Comparison and Detection
//----------------------------------------------------
InspectionResult analyzeProfile(
    const std::vector<cv::Point>& aligned,
    const std::vector<cv::Point>& reference,
    const double refStdDev)
{
    InspectionResult result;
    result.hasDent = false;
    result.alignmentDx = 0;
    result.alignmentDy = 0;
    result.alignmentSlope = 0;
    result.completeness = 1.0;
    result.processingTimeMs = 0;

    int N = aligned.size();
    if (N == 0 || reference.size() != static_cast<size_t>(N))
    {
        return result;
    }

    // Compute basic difference array
    std::vector<double> errors(N);
    double sum_sq_err = 0.0;
    double sum_abs_err = 0.0;
    double max_err = 0.0;

    for (int x = 0; x < N; ++x)
    {
        double err = aligned[x].y - reference[x].y;
        errors[x] = err;
        sum_sq_err += err * err;
        double abs_err = std::abs(err);
        sum_abs_err += abs_err;
        if (abs_err > max_err)
        {
            max_err = abs_err;
        }
    }

    result.rmse = std::sqrt(sum_sq_err / N);
    result.avgDeviation = sum_abs_err / N;
    result.maxDeviation = max_err;

    // Estimate noise level using Median Absolute Deviation (MAD)
    std::vector<double> errors_copy = errors;
    std::nth_element(errors_copy.begin(), errors_copy.begin() + N / 2, errors_copy.end());
    double median_err = errors_copy[N / 2];

    std::vector<double> abs_devs(N);
    for (int x = 0; x < N; ++x)
    {
        abs_devs[x] = std::abs(errors[x] - median_err);
    }
    std::nth_element(abs_devs.begin(), abs_devs.begin() + N / 2, abs_devs.end());
    double mad = abs_devs[N / 2];
    double noise_est = 1.4826 * mad;
    if (noise_est < 0.5) noise_est = 0.5;
    result.noiseLevel = noise_est;

    // Adaptive threshold based on noise level
    double T = 4.5 * noise_est;
    // Clamping to avoid false positives under low noise
    T = std::max(5.0, std::min(20.0, T));

    // Smooth errors using a 15-point moving average for stable detection
    std::vector<double> e_smoothed(N, 0.0);
    int W_err = 15;
    for (int i = 0; i < N; ++i)
    {
        double sum = 0.0;
        int count = 0;
        for (int k = -W_err / 2; k <= W_err / 2; ++k)
        {
            int idx = i + k;
            if (idx >= 0 && idx < N)
            {
                sum += errors[idx];
                count++;
            }
        }
        e_smoothed[i] = sum / count;
    }

    // Scan for contiguous segments where absolute smoothed error exceeds threshold
    struct Segment {
        int start;
        int end;
    };
    std::vector<Segment> candidates;
    int cur_start = -1;

    for (int x = 0; x < N; ++x)
    {
        if (std::abs(e_smoothed[x]) > T)
        {
            if (cur_start == -1)
            {
                cur_start = x;
            }
        }
        else
        {
            if (cur_start != -1)
            {
                candidates.push_back({cur_start, x - 1});
                cur_start = -1;
            }
        }
    }
    if (cur_start != -1)
    {
        candidates.push_back({cur_start, N - 1});
    }

    // Filter by minimum width 15 and merge segments with gap < 10
    std::vector<Segment> merged;
    for (const auto& seg : candidates)
    {
        int width = seg.end - seg.start + 1;
        if (width < 15) continue;

        if (merged.empty())
        {
            merged.push_back(seg);
        }
        else
        {
            auto& last = merged.back();
            if (seg.start - last.end <= 10)
            {
                last.end = seg.end;
            }
            else
            {
                merged.push_back(seg);
            }
        }
    }

    // Process each valid segment as a detected dent
    for (const auto& seg : merged)
    {
        Dent dent;
        dent.start = seg.start;
        dent.end = seg.end;
        dent.width = seg.end - seg.start + 1;
        dent.center = (seg.start + seg.end) / 2;

        // Compute peak depth within the dent segment
        double max_depth = 0.0;
        for (int x = seg.start; x <= seg.end; ++x)
        {
            double abs_err = std::abs(errors[x]);
            if (abs_err > max_depth)
            {
                max_depth = abs_err;
            }
        }
        dent.depth = max_depth;

        // Severity index based on depth and width
        double severity_score = max_depth * std::sqrt(dent.width);
        if (severity_score < 15.0)
            dent.severity = "Minor";
        else if (severity_score < 30.0)
            dent.severity = "Moderate";
        else if (severity_score < 60.0)
            dent.severity = "Major";
        else
            dent.severity = "Critical";

        // Multi-factor confidence calculation
        double ratio = max_depth / T;
        double confidence = 100.0 * (1.0 - std::exp(-0.5 * (ratio - 1.0))) * (0.8 + 0.2 * std::min(1.0, dent.width / 50.0));
        dent.confidence = std::max(40.0, std::min(100.0, confidence));

        result.dents.push_back(dent);
    }

    result.hasDent = !result.dents.empty();
    return result;
}

//----------------------------------------------------
// Milestone 6: Visualization
//----------------------------------------------------
void visualizeInspection(
    cv::Mat& output,
    const std::vector<cv::Point>& reference,
    const std::vector<cv::Point>& aligned,
    const InspectionResult& result)
{
    int N = aligned.size();
    if (N == 0 || reference.size() != static_cast<size_t>(N))
    {
        return;
    }

    // 1. Draw Reference curve (Blue)
    for (int x = 1; x < N; ++x)
    {
        cv::line(output, reference[x - 1], reference[x], cv::Scalar(255, 0, 0), 2);
    }

    // 2. Draw Aligned current curve (Green)
    for (int x = 1; x < N; ++x)
    {
        cv::line(output, aligned[x - 1], aligned[x], cv::Scalar(0, 255, 0), 1);
    }

    // 3. For each dent, draw boxes, highlight curves, and mark peak deviation
    for (const auto& dent : result.dents)
    {
        // Highlight dent portion in Red
        for (int x = dent.start; x <= dent.end; ++x)
        {
            if (x > dent.start)
            {
                cv::line(output, aligned[x - 1], aligned[x], cv::Scalar(0, 0, 255), 3);
            }
        }

        // Compute vertical bounds of the bounding box
        int min_y = 1e9, max_y = -1e9;
        int peak_x = dent.start;
        double max_dev = -1.0;
        for (int x = dent.start; x <= dent.end; ++x)
        {
            min_y = std::min({min_y, reference[x].y, aligned[x].y});
            max_y = std::max({max_y, reference[x].y, aligned[x].y});
            double dev = std::abs(aligned[x].y - reference[x].y);
            if (dev > max_dev)
            {
                max_dev = dev;
                peak_x = x;
            }
        }

        cv::Rect bbox(dent.start, min_y - 5, dent.width, (max_y - min_y) + 10);
        bbox.x = std::max(0, bbox.x);
        bbox.y = std::max(0, bbox.y);
        if (bbox.x + bbox.width > output.cols) bbox.width = output.cols - bbox.x;
        if (bbox.y + bbox.height > output.rows) bbox.height = output.rows - bbox.y;

        cv::rectangle(output, bbox, cv::Scalar(0, 0, 255), 2);

        // Draw crosshair at peak deviation point
        cv::circle(output, Point(peak_x, aligned[peak_x].y), 5, cv::Scalar(0, 0, 255), -1);
        cv::circle(output, Point(peak_x, aligned[peak_x].y), 8, cv::Scalar(0, 0, 255), 2);
    }

    // 4. Draw overlay text
    int y_offset = 25;
    if (!result.hasDent)
    {
        drawTextWithOutline(output, "INSPECTION: OK", Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(0, 255, 0), 2);
    }
    else
    {
        drawTextWithOutline(output, "INSPECTION: DENT DETECTED", Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(0, 0, 255), 2);
        y_offset += 22;
        drawTextWithOutline(output, "Dents Count: " + to_string(result.dents.size()), Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 255, 255), 1);

        // Overlay details of the largest dent
        const Dent* largest = &result.dents[0];
        for (const auto& d : result.dents)
        {
            if (d.depth > largest->depth)
            {
                largest = &d;
            }
        }
        y_offset += 20;
        drawTextWithOutline(output, "Largest Dent Details:", Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.5, cv::Scalar(255, 255, 0), 1);
        y_offset += 16;
        drawTextWithOutline(output, "  Width: " + to_string(largest->width) + " px", Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.45, cv::Scalar(255, 255, 255), 1);
        y_offset += 16;
        drawTextWithOutline(output, "  Depth: " + to_string(static_cast<int>(std::round(largest->depth))) + " px", Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.45, cv::Scalar(255, 255, 255), 1);
        y_offset += 16;
        drawTextWithOutline(output, "  Severity: " + largest->severity, Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.45, cv::Scalar(0, 0, 255), 1);
        y_offset += 16;
        drawTextWithOutline(output, "  Confidence: " + to_string(static_cast<int>(std::round(largest->confidence))) + "%", Point(15, y_offset), FONT_HERSHEY_SIMPLEX, 0.45, cv::Scalar(255, 255, 255), 1);
    }
}

//----------------------------------------------------
// Milestone 7: Statistics
//----------------------------------------------------
void printStatistics(const InspectionResult& result)
{
    cout << "==========================================================" << endl;
    cout << "                DENT DETECTED STATISTICS                  " << endl;
    cout << "==========================================================" << endl;
    cout << "Status:             " << (result.hasDent ? "DENT DETECTED" : "OK") << endl;
    cout << "Number of Dents:    " << result.dents.size() << endl;
    cout << "RMSE:               " << fixed << setprecision(2) << result.rmse << " px" << endl;
    cout << "Average Deviation:  " << result.avgDeviation << " px" << endl;
    cout << "Maximum Deviation:  " << result.maxDeviation << " px" << endl;
    cout << "Estimated Noise:    " << result.noiseLevel << " px" << endl;
    cout << "Alignment Dx:       " << result.alignmentDx << " px" << endl;
    cout << "Alignment Dy:       " << result.alignmentDy << " px" << endl;
    cout << "Alignment Slope:    " << setprecision(5) << result.alignmentSlope << endl;
    cout << "Profile Completeness: " << setprecision(1) << (result.completeness * 100.0) << "%" << endl;
    cout << "Processing Time:    " << setprecision(1) << result.processingTimeMs << " ms" << endl;
    if (result.hasDent)
    {
        cout << "----------------------------------------------------------" << endl;
        cout << "Dent Details:" << endl;
        for (size_t i = 0; i < result.dents.size(); ++i)
        {
            const auto& dent = result.dents[i];
            cout << "  Dent #" << (i + 1) << ":"
                 << " Range=[" << dent.start << " - " << dent.end << "]"
                 << " Center=" << dent.center
                 << " Width=" << dent.width << " px"
                 << " Depth=" << setprecision(1) << dent.depth << " px"
                 << " Severity=" << dent.severity
                 << " Confidence=" << setprecision(0) << dent.confidence << "%"
                 << endl;
        }
    }
    cout << "==========================================================" << endl;
}

void saveInspectionJson(const std::string& filename, const InspectionResult& result)
{
    ofstream ofs(filename);
    if (!ofs.is_open())
    {
        cerr << "Failed to open json file: " << filename << endl;
        return;
    }

    ofs << "{\n";
    ofs << "  \"dent\": " << (result.hasDent ? "true" : "false") << ",\n";
    ofs << "  \"dents_count\": " << result.dents.size() << ",\n";
    ofs << "  \"rmse\": " << fixed << setprecision(2) << result.rmse << ",\n";
    ofs << "  \"avg_deviation\": " << result.avgDeviation << ",\n";
    ofs << "  \"max_deviation\": " << result.maxDeviation << ",\n";
    ofs << "  \"noise_level\": " << result.noiseLevel << ",\n";
    ofs << "  \"alignment_dx\": " << result.alignmentDx << ",\n";
    ofs << "  \"alignment_dy\": " << result.alignmentDy << ",\n";
    ofs << "  \"alignment_slope\": " << setprecision(5) << result.alignmentSlope << ",\n";
    ofs << "  \"completeness_pct\": " << setprecision(1) << (result.completeness * 100.0) << ",\n";
    ofs << "  \"processing_time_ms\": " << result.processingTimeMs << ",\n";
    ofs << "  \"dents\": [\n";

    for (size_t i = 0; i < result.dents.size(); ++i)
    {
        const auto& dent = result.dents[i];
        ofs << "    {\n";
        ofs << "      \"id\": " << (i + 1) << ",\n";
        ofs << "      \"start\": " << dent.start << ",\n";
        ofs << "      \"end\": " << dent.end << ",\n";
        ofs << "      \"center\": " << dent.center << ",\n";
        ofs << "      \"width\": " << dent.width << ",\n";
        ofs << "      \"depth\": " << fixed << setprecision(2) << dent.depth << ",\n";
        ofs << "      \"severity\": \"" << dent.severity << "\",\n";
        ofs << "      \"confidence\": " << setprecision(1) << dent.confidence << "\n";
        ofs << "    }";
        if (i + 1 < result.dents.size())
        {
            ofs << ",";
        }
        ofs << "\n";
    }

    ofs << "  ]\n";
    ofs << "}\n";
    ofs.close();
}
