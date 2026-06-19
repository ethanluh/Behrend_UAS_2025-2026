cmake_minimum_required(VERSION 3.10)
project(uas_embedded LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(USE_OPENCV_DNN "Use OpenCV DNN instead of ONNX Runtime" OFF)

enable_testing()

# ── geometry_tests: pure C++, no OpenCV/ORT. Always builds (used by CI). ─────
add_executable(geometry_tests tests/test_geometry.cpp)
target_include_directories(geometry_tests PRIVATE src)
add_test(NAME geometry_tests COMMAND geometry_tests)

# ── yolo_infer: the real inference binary. Needs OpenCV (+ ORT by default). ──
find_package(OpenCV QUIET)
if(NOT OpenCV_FOUND)
    message(WARNING "OpenCV not found — skipping the yolo_infer target. "
                    "The geometry_tests target still builds.")
    return()
endif()

add_executable(yolo_infer src/main.cpp src/yolo_infer.cpp)
target_include_directories(yolo_infer PRIVATE src ${OpenCV_INCLUDE_DIRS})
target_link_libraries(yolo_infer PRIVATE ${OpenCV_LIBS})

if(USE_OPENCV_DNN)
    target_compile_definitions(yolo_infer PRIVATE USE_OPENCV_DNN)
else()
    # Point cmake at your ONNX Runtime install: -DONNXRUNTIME_ROOT=/path/to/ort
    find_path(ONNXRUNTIME_INCLUDE_DIR onnxruntime_cxx_api.h
              HINTS ${ONNXRUNTIME_ROOT}/include
              PATH_SUFFIXES onnxruntime onnxruntime/core/session)
    find_library(ONNXRUNTIME_LIB onnxruntime
                 HINTS ${ONNXRUNTIME_ROOT}/lib)
    if(NOT ONNXRUNTIME_INCLUDE_DIR OR NOT ONNXRUNTIME_LIB)
        message(FATAL_ERROR
            "ONNX Runtime not found. Set -DONNXRUNTIME_ROOT=/path/to/onnxruntime "
            "or configure with -DUSE_OPENCV_DNN=ON to use the OpenCV-DNN backend.")
    endif()
    target_include_directories(yolo_infer PRIVATE ${ONNXRUNTIME_INCLUDE_DIR})
    target_link_libraries(yolo_infer PRIVATE ${ONNXRUNTIME_LIB})
endif()
