# === This file is part of Calamares - <https://calamares.io> ===
#
#   SPDX-FileCopyrightText: 2020 Adriaan de Groot <groot@kde.org>
#   SPDX-License-Identifier: BSD-2-Clause
#
find_package(${qtname} ${QT_VERSION} CONFIG REQUIRED DBus Network)

if(WITH_QML)
    find_package(${qtname} REQUIRED COMPONENTS QuickWidgets)
    set(CORRY_QUICK_LIB ${qtname}::QuickWidgets)
endif()

find_package(LIBPARTED)
if(LIBPARTED_FOUND)
    set(PARTMAN_SRC checker/partman_devices.c)
    set(PARTMAN_LIB ${LIBPARTED_LIBRARY})
else()
    set(PARTMAN_SRC)
    set(PARTMAN_LIB)
    add_definitions(-DWITHOUT_LIBPARTED)
endif()

calamares_add_plugin(welcome
    TYPE viewmodule
    EXPORT_MACRO PLUGINDLLEXPORT_PRO
    SOURCES
        checker/CheckerContainer.cpp
        checker/GeneralRequirements.cpp
        checker/ResultDelegate.cpp
        checker/ResultsListWidget.cpp
        ${PARTMAN_SRC}
        WelcomeViewStep.cpp
        Config.cpp
        Config.h
        WelcomePage.cpp
    UI
        WelcomePage.ui
    RESOURCES
        welcome.qrc
    LINK_PRIVATE_LIBRARIES
        ${PARTMAN_LIB}
        ${qtname}::DBus
        ${qtname}::Network
        ${CORRY_QUICK_LIB}
    SHARED_LIB
)

calamares_add_test(
    welcometest
    SOURCES checker/GeneralRequirements.cpp ${PARTMAN_SRC} Config.cpp Tests.cpp
    LIBRARIES ${PARTMAN_LIB} ${qtname}::DBus ${qtname}::Network ${qtname}::Widgets Calamares::calamaresui
)

if(WITH_QML AND BUILD_TESTING)
    find_package(${qtname} REQUIRED COMPONENTS Multimedia)
    calamares_add_test(corrymediatest
        GUI
        SOURCES CorryMediaTests.cpp
        LIBRARIES ${qtname}::QuickWidgets ${qtname}::Multimedia
    )
endif()
