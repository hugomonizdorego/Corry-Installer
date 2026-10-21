/* === This file is part of Calamares - <https://calamares.io> ===
 *
 *   SPDX-FileCopyrightText: 2019 Adriaan de Groot <groot@kde.org>
 *   SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Calamares is Free Software: see the License-Identifier above.
 *
 */

#include "Tests.h"

#ifdef HAVE_APPDATA
#include "ItemAppData.h"
#endif
#ifdef HAVE_APPSTREAM_VERSION
#include "ItemAppStream.h"
#endif
#include "PackageModel.h"
#include "PackageChooserPage.h"

#include "utils/Logger.h"

#include <QtTest/QtTest>
#include <QListView>
#include <QPushButton>

QTEST_MAIN( PackageChooserTests )

PackageChooserTests::PackageChooserTests() {}

PackageChooserTests::~PackageChooserTests() {}

void
PackageChooserTests::initTestCase()
{
    Logger::setupLogLevel( Logger::LOGDEBUG );
}

void
PackageChooserTests::testCorryClickSelection()
{
    PackageListModel model( nullptr );
    model.addPackage( PackageItem( "office", "Office", "Documents" ) );
    model.addPackage( PackageItem( "media", "Media", "Audio and video" ) );
    model.addPackage( PackageItem( "", "Introduction", "Choose software" ) );
    PackageChooserPage page( PackageChooserMode::OptionalMultiple );
    page.setModel( &model );
    QVERIFY( page.repositoriesReady() );
    page.enableCorryRepositoryCheck();
    QVERIFY( !page.repositoriesReady() );
    auto* list = page.findChild< QListView* >( "products" );
    QVERIFY( list );
    QCOMPARE( list->selectionMode(), QAbstractItemView::MultiSelection );
    QVERIFY( list->isRowHidden( 2 ) );
    page.resize( 800, 500 );
    page.show();
    // A plain click toggles each choice; Ctrl/Shift is unnecessary.
    QTest::mouseClick( list->viewport(), Qt::LeftButton, Qt::NoModifier,
                       list->visualRect( model.index( 0, 0 ) ).center() );
    QTest::mouseClick( list->viewport(), Qt::LeftButton, Qt::NoModifier,
                       list->visualRect( model.index( 1, 0 ) ).center() );
    QCOMPARE( page.selectedPackageIds().size(), 2 );
    QTest::mouseClick( list->viewport(), Qt::LeftButton, Qt::NoModifier,
                       list->visualRect( model.index( 0, 0 ) ).center() );
    QCOMPARE( page.selectedPackageIds(), QStringList { "media" } );
    auto* skip = page.findChild< QPushButton* >( "corrySkipSoftware" );
    QVERIFY( skip );
    skip->click();
    QVERIFY( page.selectedPackageIds().isEmpty() );
}

void
PackageChooserTests::testAppData()
{
    // Path from the build-dir and from the running-the-test varies,
    // for in-source build, for build/, and for tests-in-build/,
    // so look in multiple places.
    QString appdataName( "io.calamares.calamares.appdata.xml" );
    for ( const auto& prefix : QStringList { "", "../", "../../../", "../../../../" } )
    {
        if ( QFile::exists( prefix + appdataName ) )
        {
            appdataName = prefix + appdataName;
            break;
        }
    }
    QVERIFY( QFile::exists( appdataName ) );

    QVariantMap m;
    m.insert( "appdata", appdataName );

#ifdef HAVE_XML
    PackageItem p1 = fromAppData( m );
    QVERIFY( p1.isValid() );
    QCOMPARE( p1.id, QStringLiteral( "io.calamares.calamares.desktop" ) );
    QCOMPARE( p1.name.get(), QStringLiteral( "Calamares" ) );
    // The <description> entry has precedence
    QCOMPARE( p1.description.get(), QStringLiteral( "Calamares is an installer program for Linux distributions." ) );
    // .. but en_GB doesn't have an entry in description, so uses <summary>
    QCOMPARE( p1.description.get( QLocale( "en_GB" ) ), QStringLiteral( "Calamares Linux Installer" ) );
    QCOMPARE( p1.description.get( QLocale( "nl" ) ),
              QStringLiteral( "Calamares is een installatieprogramma voor Linux distributies." ) );
    QVERIFY( p1.screenshot.isNull() );

    m.insert( "id", "calamares" );
    m.insert( "screenshot", ":/images/calamares.png" );
    PackageItem p2 = fromAppData( m );
    QVERIFY( p2.isValid() );
    QCOMPARE( p2.id, QStringLiteral( "calamares" ) );
    QCOMPARE( p2.description.get( QLocale( "nl" ) ),
              QStringLiteral( "Calamares is een installatieprogramma voor Linux distributies." ) );
    QVERIFY( !p2.screenshot.isNull() );
#endif
}
