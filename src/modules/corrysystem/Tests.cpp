/* SPDX-License-Identifier: GPL-3.0-or-later
 *
 *   Corry Installer: compatibility rules of the "System components" page.
 */
#include "Config.h"

#include "GlobalStorage.h"
#include "JobQueue.h"
#include "utils/Logger.h"
#include "utils/Yaml.h"

#include <QtTest/QtTest>

using namespace CorrySystem;

class CorrySystemTests : public QObject
{
    Q_OBJECT
public:
    CorrySystemTests() {}
    ~CorrySystemTests() override {}

private Q_SLOTS:
    void initTestCase();
    void testDefaultsAndArchitectures();
    void testOfflineKeepsDefaults();
    void testFirmwareSecureBootAndFilesystems();
    void testGnomeBlocksOtherInits();
    void testGlobalStorageAndSummary();

private:
    QVariantMap configuration();
};

QVariantMap
CorrySystemTests::configuration()
{
    // The shipped configuration, so the tests follow what users see.
    const auto path = QString::fromLatin1( BUILD_AS_TEST ) + QStringLiteral( "/corrysystem.conf" );
    bool ok = false;
    const auto map = Calamares::YAML::load( path, &ok );
    if ( !ok )
    {
        cWarning() << "Could not load" << path;
    }
    return map;
}

void
CorrySystemTests::initTestCase()
{
    Logger::setupLogLevel( Logger::LOGDEBUG );
    (void)new Calamares::JobQueue();
}

void
CorrySystemTests::testDefaultsAndArchitectures()
{
    QCOMPARE( debianArchitecture( QStringLiteral( "x86_64" ) ), QStringLiteral( "amd64" ) );
    QCOMPARE( debianArchitecture( QStringLiteral( "arm64" ) ), QStringLiteral( "arm64" ) );
    QCOMPARE( debianArchitecture( QStringLiteral( "arm" ) ), QStringLiteral( "armhf" ) );

    Config config;
    config.setConfigurationMap( configuration() );
    QCOMPARE( config.initSystems().size(), 4 );
    QCOMPARE( config.bootLoaders().size(), 5 );
    QCOMPARE( config.selectedInit(), QStringLiteral( "systemd" ) );
    QCOMPARE( config.selectedBootLoader(), QStringLiteral( "grub" ) );
    QVERIFY( config.initSystem( QStringLiteral( "systemd" ) )->isDefault );
    QVERIFY( config.bootLoader( QStringLiteral( "grub" ) )->isDefault );
    QVERIFY( config.bootLoader( QStringLiteral( "grub" ) )->packages.isEmpty() );
    QVERIFY( !config.initSystem( QStringLiteral( "sysvinit" ) )->packages.isEmpty() );
}

void
CorrySystemTests::testOfflineKeepsDefaults()
{
    Config config;
    config.setConfigurationMap( configuration() );
    Environment offline;
    offline.online = false;
    offline.firmware = QStringLiteral( "efi" );
    config.evaluate( offline );
    for ( const auto& option : config.initSystems() )
    {
        QCOMPARE( option.available, option.isDefault );
        if ( !option.isDefault )
        {
            QVERIFY( option.reason.contains( QStringLiteral( "offline" ) ) );
        }
    }
    for ( const auto& option : config.bootLoaders() )
    {
        QCOMPARE( option.available, option.isDefault );
    }
    QVERIFY( !config.selectInit( QStringLiteral( "runit" ) ) );
    QCOMPARE( config.selectedInit(), QStringLiteral( "systemd" ) );

    // Chosen online, then the connection drops: back to the default.
    Environment online = offline;
    online.online = true;
    config.evaluate( online );
    QVERIFY( config.selectInit( QStringLiteral( "runit" ) ) );
    QVERIFY( config.selectBootLoader( QStringLiteral( "refind" ) ) );
    config.evaluate( offline );
    QCOMPARE( config.selectedInit(), QStringLiteral( "systemd" ) );
    QCOMPARE( config.selectedBootLoader(), QStringLiteral( "grub" ) );
}

void
CorrySystemTests::testFirmwareSecureBootAndFilesystems()
{
    Config config;
    config.setConfigurationMap( configuration() );
    Environment bios;
    bios.online = true;
    bios.firmware = QStringLiteral( "bios" );
    bios.bootFilesystem = QStringLiteral( "ext4" );
    config.evaluate( bios );
    QVERIFY( config.bootLoader( QStringLiteral( "grub" ) )->available );
    QVERIFY( config.bootLoader( QStringLiteral( "extlinux" ) )->available );
    QVERIFY( !config.bootLoader( QStringLiteral( "systemd-boot" ) )->available );
    QVERIFY( !config.bootLoader( QStringLiteral( "refind" ) )->available );
    QVERIFY( !config.bootLoader( QStringLiteral( "uboot" ) )->available );  // amd64
    QVERIFY( config.bootLoader( QStringLiteral( "uboot" ) )->reason.contains( QStringLiteral( "amd64" ) ) );

    // Corry's default Btrfs with compression is not readable by EXTLINUX.
    Environment btrfs = bios;
    btrfs.bootFilesystem = QStringLiteral( "btrfs" );
    btrfs.bootCompressed = true;
    config.evaluate( btrfs );
    QVERIFY( !config.bootLoader( QStringLiteral( "extlinux" ) )->available );
    QVERIFY( config.bootLoader( QStringLiteral( "extlinux" ) )->reason.contains( QStringLiteral( "Btrfs" ) ) );

    Environment efi = bios;
    efi.firmware = QStringLiteral( "efi" );
    config.evaluate( efi );
    QVERIFY( config.bootLoader( QStringLiteral( "systemd-boot" ) )->available );
    QVERIFY( config.bootLoader( QStringLiteral( "refind" ) )->available );
    QVERIFY( !config.bootLoader( QStringLiteral( "extlinux" ) )->available );

    // rEFInd reads ext2/3/4 and Btrfs, but has no XFS driver.
    Environment xfs = efi;
    xfs.bootFilesystem = QStringLiteral( "xfs" );
    config.evaluate( xfs );
    QVERIFY( !config.bootLoader( QStringLiteral( "refind" ) )->available );
    QVERIFY( config.bootLoader( QStringLiteral( "systemd-boot" ) )->available );  // kernels on the ESP

    Environment secure = efi;
    secure.secureBoot = true;
    config.evaluate( secure );
    QVERIFY( config.bootLoader( QStringLiteral( "grub" ) )->available );
    for ( const auto& option : config.bootLoaders() )
    {
        if ( !option.isDefault )
        {
            QVERIFY2( !option.available, qPrintable( option.id ) );
        }
    }
    // The UEFI loaders are blocked by Secure Boot itself (Debian signs only GRUB).
    for ( const auto& id : { QStringLiteral( "systemd-boot" ), QStringLiteral( "refind" ) } )
    {
        QVERIFY2( config.bootLoader( id )->reason.contains( QStringLiteral( "Secure Boot" ) ), qPrintable( id ) );
    }
    // Init systems do not depend on the firmware.
    QVERIFY( config.initSystem( QStringLiteral( "sysvinit" ) )->available );

    Environment arm = efi;
    arm.architecture = QStringLiteral( "arm64" );
    config.evaluate( arm );
    QVERIFY( config.bootLoader( QStringLiteral( "uboot" ) )->available );

    // systemd-boot (Debian's package depends on systemd) follows the init choice.
    config.evaluate( efi );
    QVERIFY( config.selectBootLoader( QStringLiteral( "systemd-boot" ) ) );
    QVERIFY( config.selectInit( QStringLiteral( "runit" ) ) );
    QVERIFY( !config.bootLoader( QStringLiteral( "systemd-boot" ) )->available );
    QVERIFY( config.bootLoader( QStringLiteral( "systemd-boot" ) )->reason.contains( QStringLiteral( "systemd" ) ) );
    QCOMPARE( config.selectedBootLoader(), QStringLiteral( "grub" ) );
    QVERIFY( config.bootLoader( QStringLiteral( "refind" ) )->available );
    QVERIFY( config.selectInit( QStringLiteral( "systemd" ) ) );
    QVERIFY( config.bootLoader( QStringLiteral( "systemd-boot" ) )->available );
}

void
CorrySystemTests::testGnomeBlocksOtherInits()
{
    Config config;
    config.setConfigurationMap( configuration() );
    Environment gnome;
    gnome.online = true;
    gnome.gnome = true;
    config.evaluate( gnome );
    QVERIFY( config.initSystem( QStringLiteral( "systemd" ) )->available );
    for ( const auto& option : config.initSystems() )
    {
        if ( !option.isDefault )
        {
            QVERIFY( !option.available );
            QVERIFY( option.reason.contains( QStringLiteral( "GNOME" ) ) );
        }
    }
    QVERIFY( !config.selectInit( QStringLiteral( "openrc" ) ) );
}

void
CorrySystemTests::testGlobalStorageAndSummary()
{
    Config config;
    config.setConfigurationMap( configuration() );
    Environment online;
    online.online = true;
    online.firmware = QStringLiteral( "efi" );
    config.evaluate( online );
    QVERIFY( config.selectBootLoader( QStringLiteral( "refind" ) ) );
    const auto map = config.toGlobalStorage();
    QCOMPARE( map.value( QStringLiteral( "init" ) ).toMap().value( QStringLiteral( "id" ) ).toString(),
              QStringLiteral( "systemd" ) );
    const auto loader = map.value( QStringLiteral( "bootloader" ) ).toMap();
    QCOMPARE( loader.value( QStringLiteral( "id" ) ).toString(), QStringLiteral( "refind" ) );
    QVERIFY( loader.value( QStringLiteral( "packages" ) ).toStringList().contains( QStringLiteral( "refind" ) ) );
    QVERIFY( !loader.value( QStringLiteral( "default" ) ).toBool() );
    QVERIFY( map.value( QStringLiteral( "online" ) ).toBool() );
    const auto status = config.prettyStatus();
    QVERIFY( status.contains( QStringLiteral( "systemd (default)" ) ) );
    QVERIFY( status.contains( QStringLiteral( "rEFInd" ) ) );
    QVERIFY( status.contains( QStringLiteral( "removed" ) ) );
}

QTEST_GUILESS_MAIN( CorrySystemTests )

#include "utils/moc-warnings.h"

#include "Tests.moc"
