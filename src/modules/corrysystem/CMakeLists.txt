# SPDX-License-Identifier: GPL-3.0-or-later
#
# Corry's "System components" page: choice of init system and boot loader.
find_package(${qtname} ${QT_VERSION} CONFIG REQUIRED Core Gui Widgets Network)

include_directories(${PROJECT_BINARY_DIR}/src/libcalamaresui)

calamares_add_plugin(corrysystem
    TYPE viewmodule
    EXPORT_MACRO PLUGINDLLEXPORT_PRO
    SOURCES
        Config.cpp
        CorrySystemPage.cpp
        CorrySystemViewStep.cpp
    SHARED_LIB
)

calamares_add_test(
    corrysystemtest
    SOURCES
        Tests.cpp
        Config.cpp
    LIBRARIES
        ${qtname}::Gui
        ${qtname}::Widgets
)
