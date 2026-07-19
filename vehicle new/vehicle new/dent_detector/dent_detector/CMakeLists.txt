cmake_minimum_required(VERSION 3.10)

project(dent_detector)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

include_directories(
    include
    ${OpenCV_INCLUDE_DIRS}
)

add_executable(dent_detector
    src/main.cpp
    src/camera.cpp
    src/preprocess.cpp
    src/led_detector.cpp
    src/profile.cpp
    src/reference.cpp
)

target_link_libraries(dent_detector
    ${OpenCV_LIBS}
)
